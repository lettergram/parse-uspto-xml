import datetime
import html
import json
import os
import re
import sys
import traceback

from bs4 import BeautifulSoup

utils_path = os.path.abspath('utils')
sys.path.append(utils_path)

# load the psycopg to connect to postgresql
from db_interface import PGDBInterface

import setup_loggers


# setup loggers
setup_loggers.setup_root_logger()
logger = setup_loggers.setup_file_logger(__file__)


def get_filenames_from_dir(dirpaths: list):
    """Get filenames from directory"""
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
    return filenames


def parse_uspto_file(bs, keep_log: bool = False):
    """
    Parses a USPTO patent in a BeautifulSoup object.
    """

    publication_title = bs.find('invention-title').text
    publication_num = bs['file'].split("-")[0]
    publication_date = bs.find('publication-reference').find('date').text
    application_type = bs.find('application-reference')['appl-type']


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
        "application_type": application_type,
        "authors": authors, # list
        "organizations": organizations, # list
        "attorneys": attorneys, # list
        "attorney_organizations": attorney_organizations, # list
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


def write_to_db(uspto_patent, db=None):

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
                          + "authors, organizations, attorneys, attorney_organizations, "
                          + "sections, section_classes, section_class_subclasses, "
                          + "section_class_subclass_groups, "
                          + "abstract, description, claims, "
                          + "created_at, updated_at"
                          + ") VALUES ("
                          + "%s, %s, %s, %s, %s, %s, %s, %s, %s, "
                          + "%s, %s, %s, %s, %s, %s, %s, %s) "
                          + "ON CONFLICT(publication_number) "
                          + "DO UPDATE SET "
                          + "publication_title=%s, "
                          + "publication_date=%s, "
                          + "publication_type=%s, "
                          + "authors=%s, "
                          + "attorneys=%s, "
                          + "attorney_organizations=%s, "
                          + "organizations=%s, "
                          + "sections=%s, section_classes=%s, "
                          + "section_class_subclasses=%s, "
                          + "section_class_subclass_groups=%s, "
                          + "abstract=%s, description=%s, "
                          + "claims=%s, updated_at=%s", uspto_db_entry)

    return


def load_local_files(
    dirpath_list: list,
    limit_per_file: int | None = None,
    push_to: str | PGDBInterface = "db",
    keep_log: bool = False,
):
    """Load all files from local directory"""
    logger.info("LOADING FILES TO PARSE\n----------------------------")
    filenames = get_filenames_from_dir(dirpath_list)

    if (
        not (isinstance(push_to, str) and push_to.endswith('.jsonl'))
        or isinstance(push_to, PGDBInterface)
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

            bs = BeautifulSoup(patent)

            if bs.find('sequence-cwu') is not None:
                continue # Skip DNA sequence documents

            application = bs.find('us-patent-application')
            if application is None: # If no application, search for grant
                application = bs.find('us-patent-grant')
            title = "None"

            try:
                title = application.find('invention-title').text
            except Exception as e:
                logger.error(f"Error at {count}: {str(e)}")

            try:
                uspto_patent = parse_uspto_file(
                    bs=application,
                    keep_log=keep_log
                )
                if isinstance(push_to, str) and push_to.endswith(".jsonl"):
                    patent_dumps_list.append(json.dumps(uspto_patent) + "\n")
                elif isinstance(push_to, PGDBInterface):
                    write_to_db(uspto_patent, db=push_to)
                success_count += 1
                file_success_count += 1
            except Exception as e:
                exception_tuple = (count, title, e, traceback.format_exc())
                errors.append(exception_tuple)
                logger.error(f"Error: {exception_tuple}")

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
    logger.info("\n\nSuccess Count:", success_count)
    logger.info("Error Count:", len(errors))


if __name__ == "__main__":
    _arg_filenames = []
    if len(sys.argv) > 1:
        _arg_filenames = sys.argv[1:]


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
