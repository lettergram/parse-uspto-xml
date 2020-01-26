import pprint
import os
import sys
import html
from bs4 import BeautifulSoup

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
    for parties in bs.find_all('parties'):
        for applicants in parties.find_all('applicants'):
            for el in applicants.find_all('addressbook'):
                first_name = el.find('first-name').text
                last_name = el.find('last-name').text
                authors.append(first_name + " " + last_name)

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
        "authors": authors,
        "sections": list(sections.keys()),
        "section_classes": list(section_classes.keys()),
        "section_class_subclasses": list(section_class_subclasses.keys()),
        "section_class_subclass_groups": list(section_class_subclass_groups.keys()),
        "abstract": abstracts,
        "descriptions": descriptions,
        "claims": claims
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
        for classification in section-class_subclass_groups:
            print("USPTO Classification #"+str(count)+": " + classification)
            count += 1
        print("\n")
        
        count = 1
        for author in authors:
            print("Inventor #"+str(count)+": " + author)
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


def write_to_db(uspto_patent):
    
    # pp = pprint.PrettyPrinter(indent=2)

    for key in uspto_patent:
        if type(uspto_patent[key]) == list:
            if key == "section_class_subclass_groups":
                print("\n--------------------------------")
                print(uspto_patent['publication_title'])
                print(uspto_patent['publication_number'])
                print(uspto_patent['sections'])
                print(uspto_patent['section_classes'])
                print(uspto_patent['section_class_subclasses'])
                print(uspto_patent['section_class_subclass_groups'])
                print("--------------------------------")
    
    

arg_filenames = []
if len(sys.argv) > 1:
    arg_filenames = sys.argv[1:]

filenames = []
for filename in arg_filenames:
    # Load listed directories
    if os.path.isdir(filename):
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

count = 1
success, errors = [], []
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
                write_to_db(uspto_patent)
                success.append(title)
            except Exception as e:
                exception_tuple = (count, title, e)
                errors.append(exception_tuple)
                print(exception_tuple)
       
            if (len(success)+len(errors)) % 70 == 0:
                print(count, filename, title)
            count += 1


print("Errors")
for e in errors:
    print(e)
    
print("Success Count:", len(success))
print("Error Count:", len(errors))
