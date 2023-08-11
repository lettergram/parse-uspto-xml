from __future__ import annotations

import datetime
import html
import json
import os
import re
import sys
import traceback
from typing import Union

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

    grant_date = bs.get("date-produced", None)

    publication_title = bs.find('invention-title').text
    publication_num = bs['file'].split("-")[0]
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
        if related_doc_bs.name in ["continuation", "division", "continuation-in-part", "reissue", "substitution"]:
            related_doc["document_type"] = related_doc_bs.name
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
        for inventors in parties.find_all(re.compile('inventors')):
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


def write_patent_to_db(uspto_patent, db=None):

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

    # Will use for created_at & updated_at time
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # INSERTS INTO DB
    uspto_db_entry = [
        uspto_patent['publication_title'],
        uspto_patent['publication_number'],
        uspto_patent['publication_date'],
        uspto_patent['application_type'],
        uspto_patent['grant_date'],
        uspto_patent['application_num'],
        uspto_patent['application_date'],
        ','.join(uspto_patent['authors']),
        ','.join(uspto_patent['organizations']),
        ','.join(uspto_patent['attorneys']),
        ','.join(uspto_patent['attorney_organizations']),
        ','.join(uspto_patent['sections']),
        ','.join(uspto_patent['section_classes']),
        ','.join(uspto_patent['section_class_subclasses']),
        ','.join(uspto_patent['section_class_subclass_groups']),
        '\n'.join(uspto_patent['abstract']),
        '\n'.join(uspto_patent['descriptions']),
        '\n'.join(uspto_patent['claims']),
        current_time,
        current_time
    ]

    # ON CONFLICT UPDATES TO DB
    uspto_db_entry += [
        uspto_patent['publication_title'],
        uspto_patent['publication_date'],
        uspto_patent['application_type'],
        uspto_patent['grant_date'],
        uspto_patent['application_num'],
        uspto_patent['application_date'],
        ','.join(uspto_patent['authors']),
        ','.join(uspto_patent['organizations']),
        ','.join(uspto_patent['attorneys']),
        ','.join(uspto_patent['attorney_organizations']),
        ','.join(uspto_patent['sections']),
        ','.join(uspto_patent['section_classes']),
        ','.join(uspto_patent['section_class_subclasses']),
        ','.join(uspto_patent['section_class_subclass_groups']),
        '\n'.join(uspto_patent['abstract']),
        '\n'.join(uspto_patent['descriptions']),
        '\n'.join(uspto_patent['claims']),
        current_time
    ]

    db_cursor = None
    if db is not None:
        db_cursor = db.obtain_db_cursor()

    if db_cursor is not None:

        db_cursor.execute("INSERT INTO uspto_patents ("
                          + "publication_title, publication_number, "
                          + "publication_date, publication_type, "
                          + "grant_date, application_num, application_date, "
                          + "authors, organizations, attorneys, attorney_organizations, "
                          + "sections, section_classes, section_class_subclasses, "
                          + "section_class_subclass_groups, "
                          + "abstract, description, claims, "
                          + "created_at, updated_at"
                          + ") VALUES ("
                          + "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
                          + "%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                          + "ON CONFLICT(publication_number) "
                          + "DO UPDATE SET "
                          + "publication_title=%s, "
                          + "publication_date=%s, "
                          + "publication_type=%s, "
                          + "grant_date=%s, "
                          + "application_num=%s, "
                          + "application_date=%s, "
                          + "authors=%s, "
                          + "attorneys=%s, "
                          + "attorney_organizations=%s, "
                          + "organizations=%s, "
                          + "sections=%s, section_classes=%s, "
                          + "section_class_subclasses=%s, "
                          + "section_class_subclass_groups=%s, "
                          + "abstract=%s, description=%s, "
                          + "claims=%s, updated_at=%s", uspto_db_entry)
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


def load_local_files(
        dirpath_list:  list,
        limit_per_file: Union[int, None] = None,
        push_to: Union[str, PGDBInterface] = "db",
        keep_log: bool = False,
):
    """Load all files from local directory"""
    logger.info("LOADING FILES TO PARSE\n----------------------------")
    filenames = get_filenames_from_dir(dirpath_list)

    if (
        not (isinstance(push_to, str) and push_to.endswith('.jsonl'))
            and not isinstance(push_to, PGDBInterface)
    ):
        push_to_error = (
            f"push_to: `{str(push_to)}` is not valid."
            " must be a str ending in 'jsonl' or a PGDBInterface."
        )
        logger.error(push_to_error)
        raise ValueError(push_to_error)

    count = 1
    success_count = 0
    errors = []
    patent_dumps_list = []
    for filename in filenames:
        file_success_count = 0
        if not filename.endswith(".xml"):
            continue

        with open(filename, "r") as fp:
            xml_text = html.unescape(fp.read())

        xml_splits = xml_text.split("<?xml version=\"1.0\" encoding=\"UTF-8\"?>")
        for patent in xml_splits:
            if limit_per_file and file_success_count >= limit_per_file:
                if file_success_count:
                    logger.info(f"{count}, {filename}, {title}")
                    if isinstance(push_to, str) and push_to.endswith(".jsonl"):
                        with open(push_to, "a") as fp:
                            fp.writelines(patent_dumps_list)
                        patent_dumps_list = []
                    elif isinstance(push_to, PGDBInterface):
                        push_to.commit_to_db()
                break

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
                if isinstance(push_to, str) and push_to.endswith(".jsonl"):
                    patent_dumps_list.append(json.dumps(uspto_patent) + "\n")
                elif isinstance(push_to, PGDBInterface):
                    write_patent_to_db(uspto_patent, db=push_to)
                    write_referential_documents_to_db(
                        uspto_patent["referential_documents"], db=push_to
                    )
                success_count += 1
                file_success_count += 1
            except Exception as e:
                exception_tuple = (count, title, e, traceback.format_exc())
                errors.append(exception_tuple)
                logger.error(f"Error: {exception_tuple}", e)

            if (success_count+len(errors)) % 50 == 0:
                logger.info(f"{count}, {filename}, {title}")
                if isinstance(push_to, str) and push_to.endswith(".jsonl"):
                    with open(push_to, "a") as fp:
                        fp.writelines(patent_dumps_list)
                    patent_dumps_list = []
                elif isinstance(push_to, PGDBInterface):
                    push_to.commit_to_db()
            count += 1

    if errors:
        logger.error("\n\nErrors\n------------------------\n")
        for e in errors:
            logger.error(e)
    logger.info("=" * 50)
    logger.info("=" * 50)
    logger.info(f"Success Count: {success_count}")
    logger.info(f"Error Count: {len(errors)}")


if __name__ == "__main__":
    _arg_filenames = []
    if len(sys.argv) > 1:
        _arg_filenames = sys.argv[1:]
    _arg_filenames = "../embedding-testing-suite/data/2022/ipg220104.xml"

    _db_config_file = "config/postgres.tsv"
    _db = PGDBInterface(config_file=_db_config_file)
    _db.silent_logging = True
    _push_to = _db

    load_local_files(
        dirpath_list=_arg_filenames,
        limit_per_file=None,
        push_to=_push_to,
        keep_log=False,
    )
