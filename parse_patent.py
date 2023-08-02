import datetime
import html
import os
import re
import sys

from bs4 import BeautifulSoup

utils_path = os.path.abspath('utils')
sys.path.append(utils_path)

# load the psycopg to connect to postgresql
from db_interface import PGDBInterface


def print_lines(text):
    """
    Prints line by line, with the line number
    """
    count = 1
    for line in text.split("\n"):
        print(count, line)
        count += 1

def parse_uspto_file(bs, logging=False):
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

    authors = []
    organizations = []
    attorneys = []
    attorney_organizations = []
    for parties in bs.find_all(re.compile('^.*parties')):
        for inventors in parties.find_all(re.compile('inventors')):
            for el in inventors.find_all('addressbook'):
                first_name = el.find('first-name').text
                last_name = el.find('last-name').text
                authors.append(first_name + " " + last_name)

        for applicants in parties.find_all(re.compile('^.*applicants')):
            for el in applicants.find_all('addressbook'):
                orgname = getattr(el.find('orgname'), "text", "")
                if not orgname:
                    continue
                org_builder = [orgname]
                for attr_name in ["city", "country"]:
                    value = getattr(el.find(attr_name), "text", "")
                    if value and value != "unknown":
                        org_builder += [value]
                # org_builder: [organization, city, country]
                organizations.append(", ".join(org_builder))

        for agents in parties.find_all(re.compile('^.*agents')):
            for agent in agents.find_all("agent", attrs={"rep-type": "attorney"}):
                for el in agent.find_all("addressbook"):

                    orgname = getattr(el.find('orgname'), "text", "")
                    if orgname:
                        org_builder = [orgname]
                        for attr_name in ["city", "country"]:
                            value = getattr(el.find(attr_name), "text", "")
                            if value and value != "unknown":
                                org_builder += [value]
                        # org_builder: [organization, city, country]
                        attorney_organizations.append(", ".join(org_builder))

                    first_name = getattr(el.find("first-name"), "text", "")
                    if first_name:
                        last_name = getattr(el.find("last-name"), "text", "")
                        attorneys.append(first_name + " " + last_name)


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

    if logging:

        # print(bs.prettify())

        print("Filename:", filename)
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

    title = "Shower shield system for bathroom shower drain areaways"
    if bs.find('invention-title').text == title:
        print(bs)
        exit()


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


arg_filenames = []
if len(sys.argv) > 1:
    arg_filenames = sys.argv[1:]

filenames = []
for filename in arg_filenames:
    # Load listed directories
    if os.path.isdir(filename):
        print("directory", filename)
        for dir_filename in os.listdir(filename):
            directory = filename
            if directory[-1] != "/":
                directory += "/"
            filenames.append(directory + dir_filename)

    # Load listed files
    if ".xml" in filename:
        filenames.append(filename)

print("LOADING FILES TO PARSE\n----------------------------")
for filename in filenames:
    print(filename)


db_config_file = "config/postgres.tsv"
db = PGDBInterface(config_file=db_config_file)
db.silent_logging = True

count = 1
success_count = 0
errors = []
for filename in filenames:
    if ".xml" in filename:

        xml_text = html.unescape(open(filename, 'r').read())

        for patent in xml_text.split("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"):

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
                print("Error", count, e)

            try:
                uspto_patent = parse_uspto_file(application)
                write_to_db(uspto_patent, db=db)
                success_count += 1
            except Exception as e:
                exception_tuple = (count, title, e)
                errors.append(exception_tuple)
                print(exception_tuple)

            if (success_count+len(errors)) % 50 == 0:
                print(count, filename, title)
                db.commit_to_db()
            count += 1


print("\n\nErrors\n------------------------\n")
for e in errors:
    print(e)

print("Success Count:", success_count)
print("Error Count:", len(errors))
