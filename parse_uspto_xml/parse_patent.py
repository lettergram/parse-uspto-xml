from __future__ import annotations

import datetime
import html
import json
import os
import re
import sys
from typing import Union, Callable

from bs4 import BeautifulSoup
import psycopg2.extras

# load the psycopg to connect to postgresql
from parse_uspto_xml import setup_loggers
from parse_uspto_xml.utils.db_interface import PGDBInterface


# setup loggers
setup_loggers.setup_root_logger()
logger = setup_loggers.setup_file_logger(__file__)


def get_filenames_from_dir(dirpaths: list | str):
    """Get filenames from directory"""

    if isinstance(dirpaths, str):
        dirpaths = [dirpaths]

    filenames = []
    for dirpath in dirpaths:
        # Load listed directories
        if os.path.isdir(dirpath):
            logger.info(f"directory: {dirpath}")
            for filename in os.listdir(dirpath):
                fullpath = os.path.join(dirpath, filename)
                dir_filenames = [fullpath]
                if os.path.isdir(fullpath):
                    dir_filenames = get_filenames_from_dir([fullpath])
                filenames += dir_filenames
        else:
            filenames += [dirpath]
    return filenames


def parse_uspto_file(bs, keep_log: bool = False):
    """
    Parses a USPTO patent in a BeautifulSoup object.
    """

    grant_date = None
    publication_num = bs['file'].split("-")[0]
    if bs.name == ('us-patent-grant'):
        grant_date = bs.get("date-produced", None)

    publication_title = bs.find('invention-title').text
    publication_date = bs.find('publication-reference').find('date').text
    application_ref_bs = bs.find('application-reference')
    application_type = application_ref_bs['appl-type']
    application_date = application_ref_bs.find('date').text
    application_num = application_ref_bs.find('doc-number').text

    referential_documents = []
    # {uspto_patents.publication_number,reference,cited_by_examiner,document_type,country,metadata (JSON)

    related_docs_bs = bs.find("us-related-documents")
    for related_doc_bs in (related_docs_bs.find_all(recursive=False) if related_docs_bs else []):
        related_doc = {
            "uspto_publication_number": publication_num,
            "reference": None,
            "cited_by_examiner": None,
            "document_type": None,
            "country": None,
            "kind": None,
            "metadata": {}
        }
        if related_doc_bs.name in ["continuation", "division", "continuation-in-part", "reissue", "substitution", "us-reexamination-reissue-merger", "continuing-reissue"]:
            document_type = related_doc_bs.name
            if document_type in ["us-reexamination-reissue-merger", "continuing-reissue"]:
                document_type = "reissue"
            related_doc["document_type"] = document_type
            related_doc["cited_by_examiner"] = False
            for documents_bs in related_doc_bs.find_all(re.compile("(parent|child)-doc(ument)?$")):
                for doc_bs in documents_bs.find_all("document-id"):
                    if doc_bs.parent.name == "parent-grant-document":
                        related_doc["reference"] = doc_bs.find("doc-number").text
                    elif doc_bs.parent.name == "parent-pct-document":
                        related_doc["metadata"]["parent_pct_number"] = doc_bs.find("doc-number").text
                        related_doc["metadata"]["parent_pct_country"] = doc_bs.find("country").text
                        related_doc["metadata"]["parent_pct_date"] = getattr(doc_bs.find("date"), "text", None)
                    elif doc_bs.parent.name == "parent-doc":
                        related_doc["country"] = doc_bs.find("country").text
                        related_doc["metadata"]["application_number"] = doc_bs.find("doc-number").text
                        related_doc["metadata"]["application_date"] = getattr(doc_bs.find("date"), "text", None)
                    elif doc_bs.parent.name == "child-doc":
                        related_doc["metadata"]["child_application_number"] = doc_bs.find("doc-number").text
                        related_doc["metadata"]["parent_country"] = doc_bs.find("country").text
        elif related_doc_bs.name in ["us-provisional-application"]:
            related_doc["document_type"] = "provisional"
            related_doc["cited_by_examiner"] = False
            related_doc["country"] = related_doc_bs.find("country").text
            related_doc["reference"] = related_doc_bs.find("doc-number").text
            related_doc["metadata"]["application_date"] = related_doc_bs.find("date").text
        elif related_doc_bs.name in ["related-publication"]:
            related_doc["document_type"] = "prior"
            related_doc["cited_by_examiner"] = False
            related_doc["reference"] = related_doc_bs.find("doc-number").text
            related_doc["country"] = related_doc_bs.find("country").text
            related_doc["kind"] = related_doc_bs.find("kind").text
            related_doc["metadata"]["date"] = related_doc_bs.find("date").text
        else:
            raise KeyError(f"'{related_doc_bs.name}' is not setup to be included in referential documents.")
        referential_documents.append(related_doc)

    references = []
    refs_cited_bs = bs.find(re.compile(".*-references-cited"))
    if refs_cited_bs:
        for ref_bs in refs_cited_bs.find_all(re.compile(".*-citation")):
            doc_bs = ref_bs.find("document-id")
            if doc_bs:
                reference = {
                    "uspto_publication_number": publication_num,
                    "reference": doc_bs.find("doc-number").text,
                    "cited_by_examiner": "examiner" in ref_bs.find("category").text,
                    "document_type": "patent-reference",
                    "country": getattr(doc_bs.find("country"), "text", None),
                    "kind": getattr(doc_bs.find("kind"), "text", None),
                    "metadata":{
                        "name": getattr(doc_bs.find("name"), "text", None),
                        "date": getattr(doc_bs.find("date"), "text", None),
                    }
                }
            else:
                reference = {
                    "uspto_publication_number": publication_num,
                    "reference": ref_bs.find("othercit").text,
                    "cited_by_examiner": "examiner" in ref_bs.find("category").text,
                    "document_type": "other-reference",
                    "country": getattr(ref_bs.find("country"), "text", None),
                    "kind": None,
                    "metadata": {},
                }
            references.append(reference)
        referential_documents += references

    priority_claims = []
    priority_docs_bs = bs.find("priority-claims")
    if priority_docs_bs:
        for doc_bs in priority_docs_bs.find_all("priority-claim"):
            priority_claims.append({
                "uspto_publication_number": publication_num,
                "reference": doc_bs.find("doc-number").text,
                "cited_by_examiner": False,
                "document_type": "other-reference",
                "country": getattr(doc_bs.find("country"), "text", None),
                "kind": None,
                "metadata":{
                    "date": getattr(doc_bs.find("date"), "text", None),
                },
            })
        referential_documents += priority_claims

    # check to make sure all keys are proper -- TODO: this should be a test.
    for reference in referential_documents:
        expected_keys = {
            "uspto_publication_number",
            "reference",
            "cited_by_examiner",
            "document_type",
            "country",
            "kind",
            "metadata",
        }
        missing_keys = expected_keys - set(reference.keys())
        bad_keys =  set(reference.keys()) - expected_keys
        if missing_keys or bad_keys:
            raise KeyError(
                f"referential_documents has missing_keys: "
                f"{missing_keys} and bad_keys: {bad_keys} "
                f"for {reference}"
            )

    # International Patent Classification (IPC) Docs:
    # https://www.wipo.int/classifications/ipc/en/
    sections = {}
    section_classes = {}
    section_class_subclasses = {}
    section_class_subclass_groups = {}
    for classes in bs.find_all('classifications-ipcr'):
        for el in classes.find_all('classification-ipcr'):

            section = el.find('section').text

            classification  = section
            classification += el.find('class').text
            classification += el.find('subclass').text

            group = el.find('main-group').text + "/"
            group += el.find('subgroup').text

            sections[section] = True
            section_classes[section+el.find('class').text] = True
            section_class_subclasses[classification] = True
            section_class_subclass_groups[classification+" "+group] = True

    if not sections:
        re_classification = re.compile(
            "(?P<section>[A-Z])"
            + "(?P<class>[0-9]{2})"
            + "(?P<subclass>[A-Z])"
            + "\s?(?P<maingroup>[0-9]{1,4})"
            + "\s?/\s?"
            + "(?P<subgroup>[0-9]{2,6})"
        )
        re_classification_tag = re.compile(
            "(classification-ipc(r)?)|(classification-cpc(-text)?)"
        )
        for classes in bs.find_all(re.compile("us-bibliographic-data-(grant|application)")):
            for el in classes.find_all(re_classification_tag):
                if "citation" in el.parent.name:
                    continue  # skip anything that's not the patent itself
                classification = getattr(el.find('main-classification'), "text", el.text)
                re_value = re_classification.match(classification)
                if re_value is not None:
                    section = re_value.group("section")
                    section_class = section + re_value.group("class")
                    section_subclass = section_class + re_value.group("subclass")

                    group = re_value.group("maingroup") + "/" + re_value.group("subgroup")

                    sections[section] = True
                    section_classes[section_class] = True
                    section_class_subclasses[section_subclass] = True
                    section_class_subclass_groups[section_subclass + " " + group] = True

    def build_name(bs_el):
        """Creates a name '<First> <Last>'"""
        # [First Name, Last Name]
        name_builder = []
        for attr_name in ["first-name", "last-name"]:
            value = getattr(bs_el.find(attr_name), "text", "")
            if value and value != "unknown":
                name_builder.append(value)
        name = ""
        if name_builder:
            name = " ".join(name_builder).strip()
        return name

    def build_org(bs_el):
        """Creates an organization '<org>, <city>, <country>'"""
        # org_builder: [organization, city, country]
        org_builder = []
        for attr_name in ["orgname", "city", "country"]:
            value = getattr(bs_el.find(attr_name), "text", "")
            if value and value != "unknown":
                org_builder.append(value)
        org_name = ""
        if org_builder:
            org_name = ", ".join(org_builder).strip()
        return org_name

    authors = []
    organizations = []
    attorneys = []
    attorney_organizations = []
    for parties in bs.find_all(re.compile('^.*parties')):
        for inventors in parties.find_all(re.compile('inventors|applicants')):
            for el in inventors.find_all('addressbook'):
                # inventor_name: " ".join([first, last])
                inventor_name = build_name(el)
                if inventor_name:
                    authors.append(inventor_name)

        for applicants in parties.find_all(re.compile('^.*applicants')):
            for el in applicants.find_all('addressbook'):
                # org_name: ", ".join([organization, city, country])
                org_name = build_org(el)
                if org_name:
                    organizations.append(org_name)

        for agents in parties.find_all(re.compile('^.*agents')):
            for agent in agents.find_all("agent", attrs={"rep-type": "attorney"}):
                for el in agent.find_all("addressbook"):
                    # attorney_name: " ".join([first, last])
                    attorney_name = build_name(el)
                    if attorney_name:
                        attorneys.append(attorney_name)

                    # org_name: ", ".join([organization, city, country])
                    org_name = build_org(el)
                    if org_name:
                        attorney_organizations.append(org_name)

    abstracts = []
    for el in bs.find_all('abstract'):
        abstracts.append(el.text.strip('\n'))

    descriptions = []
    for el in bs.find_all('description'):
        descriptions.append(el.text.strip('\n'))

    claims = []
    for el in bs.find_all('claim'):
        claims.append(el.text.strip('\n'))

    uspto_patent = {
        "publication_title": publication_title,
        "publication_number": publication_num,
        "publication_date": publication_date,
        "grant_date": grant_date,
        "application_num": application_num,
        "application_type": application_type,
        "application_date": application_date,
        "authors": authors, # list
        "organizations": organizations, # list
        "attorneys": attorneys, # list
        "attorney_organizations": attorney_organizations, # list
        "referential_documents": referential_documents,
        "sections": list(sections.keys()),
        "section_classes": list(section_classes.keys()),
        "section_class_subclasses": list(section_class_subclasses.keys()),
        "section_class_subclass_groups": list(section_class_subclass_groups.keys()),
        "abstract": abstracts, # list
        "descriptions": descriptions, # list
        "claims": claims # list
    }

    if keep_log:

        print("Filename:", bs['file'])
        print("\n\n")
        print("\n--------------------------------------------------------\n")

        print("USPTO Invention Title:", publication_title)
        print("USPTO Publication Number:", publication_num)
        print("USPTO Publication Date:", publication_date)
        print("USPTO Application Type:", application_type)

        count = 1
        for classification in section_class_subclass_groups:
            print("USPTO Classification #"+str(count)+": " + classification)
            count += 1
        print("\n")

        count = 1
        for author in authors:
            print("Inventor #"+str(count)+": " + author)
            count += 1

        count = 1
        for org in organizations:
            print("Organization #"+str(count)+": " + org)
            count += 1

        count = 1
        for attorney in attorneys:
            print("Attorney #"+str(count)+": " + attorney)
            count += 1

        count = 1
        for org in attorney_organizations:
            print("Attorney Organization #"+str(count)+": " + org)
            count += 1

        print("\n--------------------------------------------------------\n")

        print("Abstract:\n-----------------------------------------------")
        for abstract in abstracts:
            print(abstract)

        print("Description:\n-----------------------------------------------")
        for description in descriptions:
            print(description)

        print("Claims:\n-----------------------------------------------")
        for claim in claims:
            print(claim)

    return uspto_patent


def write_patent_to_db(patents, patent_table_name, db=None):

    """
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    for key in uspto_patent:
        if type(uspto_patent[key]) == list:
            if key == "section_class_subclass_groups":
                print("\n--------------------------------")
                print(uspto_patent['publication_title'])
                print(uspto_patent['publication_number'])
                print(uspto_patent['publication_date'])
                print(uspto_patent['sections'])
                print(uspto_patent['section_classes'])
                print(uspto_patent['section_class_subclasses'])
                print(uspto_patent['section_class_subclass_groups'])
                print("--------------------------------")
    """

    db_cursor = None
    if db is not None:
        db_cursor = db.obtain_db_cursor()

    if db_cursor is None:
        return

    columns = [
        "publication_title",
        "publication_number",
        "publication_date",
        "publication_type",
        "grant_date",
        "application_num",
        "application_date",
        "authors",
        "organizations",
        "attorneys",
        "attorney_organizations",
        "sections",
        "section_classes",
        "section_class_subclasses",
        "section_class_subclass_groups",
        "abstract",
        "description",
        "claims",
        "created_at",
        "updated_at",
    ]
    read_only_cols = {"created_at"}
    conflict_columns = {"publication_number"}
    updateable_cols = set(columns).difference(conflict_columns).difference(read_only_cols)

    def tuple_creator(values):
        n_values = len(values)
        format_str = ', '.join(["\"{}\""] * n_values)
        return f"({format_str})".format(*values)

    def jsonify_dicts(value):
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    def get_data_for_column(data, column):
        if column in ["created_at", "updated_at"]:
            return current_time
        elif column in ["publication_type"]:
            return data.get("application_type")
        elif column in ["abstract", "description", "claims"]:
            if column == "description":
                column = "descriptions"
            return '\n'.join(data.get(column))
        elif column in [
            "authors", "organizations", "attorneys", "attorney_organizations",
            "sections", "section_classes", "section_class_subclasses",
            "section_class_subclass_groups",
        ]:
            return ','.join(data.get(column))
        return data.get(column)

    exclude_set_string = "({})".format(", ".join([
        "EXCLUDED.{:s}".format(col) for col in updateable_cols
    ]))

    # Will use for created_at & updated_at time
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    psycopg2.extras.execute_values(
        db_cursor,
        f"""INSERT INTO {patent_table_name} {tuple_creator(columns)}
                VALUES
                    %s
                ON CONFLICT {tuple_creator(conflict_columns)} DO UPDATE
                SET {tuple_creator(updateable_cols)} = {exclude_set_string}""",
        [
            [ jsonify_dicts(get_data_for_column(data, column)) for column in columns ]
                for data in patents
        ]
    )
    logger.debug(f"DB UPSERT message: {db_cursor.statusmessage}")
    return


def write_referential_documents_to_db(document_list, db=None):
    """"""
    # Will use for created_at & updated_at time
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


    db_cursor = None
    if db is not None:
        db_cursor = db.obtain_db_cursor()

    if db_cursor is None:
        return

    columns = [
        "uspto_publication_number",
        "reference",
        "cited_by_examiner",
        "document_type",
        "country",
        "metadata",
        "kind",
        "created_at",
        "updated_at",
    ]
    # read_only_cols = {"created_at"}
    # conflict_columns = {"uspto_publication_number", "reference", "document_type", "country", "kind"}
    # updateable_cols = set(columns).difference(conflict_columns).difference(read_only_cols)
    # conflict_columns = {"uspto_publication_number", "reference", "document_type", "country", "kind"}

    def tuple_creator(values):
        n_values = len(values)
        format_str = ', '.join(["\"{}\""] * n_values)
        return f"({format_str})".format(*values)

    def jsonify_dicts(value):
        if isinstance(value, dict):
            return json.dumps(value)
        return value

    def get_data_for_column(data, column):
        if column in ["created_at", "updated_at"]:
            return current_time
        return data.get(column)

    # exclude_set_string = "({})".format(", ".join([
    #     "EXCLUDED.{:s}".format(col) for col in updateable_cols
    # ]))

    psycopg2.extras.execute_values(
        db_cursor,
        f"""INSERT INTO uspto_referential_documents {tuple_creator(columns)}
                VALUES
                    %s
                ON CONFLICT DO NOTHING""",
                # ON CONFLICT {tuple_creator(conflict_columns)} DO UPDATE
                # SET {tuple_creator(updateable_cols)} = {exclude_set_string}""",
        [
            [ jsonify_dicts(get_data_for_column(data, column)) for column in columns ]
                for data in document_list
        ]
    )
    logger.debug(f"DB UPSERT message: {db_cursor.statusmessage}")
    return


def load_batch_from_data(
        xml_text_list: list[str],
        keep_log: bool = False
    ):

    count = 0
    success_count = 0
    errors = []
    patent_list = []

    for patent in xml_text_list:

        if patent is None or patent == "":
            continue

        bs = BeautifulSoup(patent, "lxml")

        if bs.find('sequence-cwu') is not None:
            continue # Skip DNA sequence documents

        application = bs.find('us-patent-application')
        if application is None: # If no application, search for grant
            application = bs.find('us-patent-grant')
        title = "None"

        try:
            title = application.find('invention-title').text
        except Exception as e:
            logger.error(f"Error at {count}: {str(e)}", e)

        try:
            uspto_patent = parse_uspto_file(
                bs=application,
                keep_log=keep_log
            )
            patent_list.append(uspto_patent)
            success_count += 1
        except Exception as e:
            exception_tuple = (count, title, e)
            errors.append(exception_tuple)
            logger.error(f"Error: {exception_tuple}", exc_info=True)
        count += 1

    return count, success_count, patent_list, errors


def load_from_data(
        xml_text: str,
        filename: str,
        push_to_func: Callable,
        batch_size: int = 50,
        max_patents: int | None = None,
        keep_log: bool = False
    ):

    count = 0
    success_count = 0
    errors = []

    xml_splits = xml_text.split("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
    if len(xml_splits) and not xml_splits[0]:
        xml_splits = xml_splits[1:]
    for i in range(0, len(xml_splits), batch_size):

        last_index = i + batch_size
        if max_patents:
            last_index = min(max_patents, i + batch_size)

        xml_batch = xml_splits[i : last_index]
        batch_count, batch_success_count, patents, batch_errors = \
            load_batch_from_data(xml_batch, keep_log)
        count += batch_count

        recent_title = None
        if len(patents):
            recent_title = patents[0].get("publication_title")

        try:
            push_to_func(patents)
            logger.info(f"{count}, {filename}, {recent_title}")
        except Exception as e:
            exception_tuple = (count, recent_title, e)
            errors.append(exception_tuple)
            logger.error(f"Error: {exception_tuple}", exc_info=True)
            batch_success_count = 0

        success_count += batch_success_count
        errors += batch_errors

        if max_patents is not None and count >= max_patents:
            break

    return count, success_count, errors


def load_local_files(
        dirpath_list:  list,
        push_to_func: Callable,
        limit_per_file: Union[int, None] = None,
        batch_size: int = 50,
        keep_log: bool = False,
):
    """Load all files from local directory"""
    logger.info("LOADING FILES TO PARSE\n----------------------------")
    filenames = get_filenames_from_dir(dirpath_list)

    count = 0
    success_count = 0
    errors = []
    for filename in filenames:
        if not filename.endswith(".xml"):
            continue

        with open(filename, "r") as fp:
            xml_text = html.unescape(fp.read())

        batch_count, batch_success_count, batch_errors = load_from_data(
            xml_text,
            filename,
            push_to_func,
            batch_size,
            max_patents=limit_per_file,
            keep_log=keep_log,
        )
        count += batch_count
        success_count += batch_success_count
        errors += batch_errors

    if errors:
        logger.error("\n\nErrors\n------------------------\n")
        for e in errors:
            logger.error(e)
    logger.info("=" * 50)
    logger.info("=" * 50)
    logger.info(f"Success Count: {success_count}")
    logger.info(f"Error Count: {count - success_count}")


def push_to_jsonl(patents: list[dict], push_to: str):
    patent_dumps_list = []
    for uspto_patent in patents:
        patent_dumps_list.append(json.dumps(uspto_patent) + "\n")
    with open(push_to, "a") as fp:
        fp.writelines(patent_dumps_list)


def push_to_db(
        patents: list[dict],
        push_to: PGDBInterface,
        patent_table_name: str,
        include_referential: bool = True,
    ):
    write_patent_to_db(patents, patent_table_name, db=push_to)
    if include_referential:
        for uspto_patent in patents:
            write_referential_documents_to_db(
                uspto_patent["referential_documents"], db=push_to
            )


def get_dump_function(push_to, *args, **kwargs):
    if isinstance(push_to, str) and push_to.endswith(".jsonl"):
        return lambda x: push_to_jsonl(x, push_to)
    elif isinstance(push_to, PGDBInterface):
        return lambda x: push_to_db(x, push_to, *args, **kwargs)
    else:
        push_to_error = (
            f"push_to: `{str(push_to)}` is not valid."
            " must be a str ending in 'jsonl' or a PGDBInterface."
        )
        logger.error(push_to_error)
        raise ValueError(push_to_error)


if __name__ == "__main__":
    _arg_filenames = []
    if len(sys.argv) > 1:
        _arg_filenames = sys.argv[1:]

    _db_config_file = "config/postgres.tsv"
    _db = PGDBInterface(config_file=_db_config_file)
    _db.silent_logging = True
    _push_to = _db
    _patent_table_name = "uspto_patents"

    _push_to_func = get_dump_function(
        _push_to,
        patent_table_name=_patent_table_name,
        include_referential=True
    )

    load_local_files(
        dirpath_list=_arg_filenames,
        push_to_func=_push_to_func,
        batch_size=50,
        limit_per_file=None,
        keep_log=False,
    )
