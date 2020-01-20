import os 
import html
from bs4 import BeautifulSoup

def parse_uspto_file(bs, logging=False):
    """
    Parses a USPTO patent in a BeautifulSoup object.
    """
    
    """
    count = 1
    for line in xml_text.split("\n"):    
        print(count, line)
        count += 1
    """

    publication_title = bs.find('invention-title').text
    publication_num = bs['file'].split("-")[0]
    publication_date = bs.find('publication-reference').find('date').text
    application_type = bs.find('application-reference')['appl-type']

    classifications = []
    for classes in bs.find_all('classifications-ipcr'):
        for el in classes.find_all('classification-ipcr'):        
            classification  = el.find('section').text
            classification += el.find('class').text
            classification += el.find('subclass').text
            classifications.append(classification)

    authors = []
    for parties in bs.find_all('parties'):
        for applicants in parties.find_all('applicants'):
            for el in applicants.find_all('addressbook'):
                first_name = el.find('first-name').text
                last_name = el.find('last-name').text
                authors.append(first_name + " " + last_name)

    abstracts = []
    for el in bs.find_all('abstract'):
        abstracts.append(el.text)
    
    descriptions = []
    for el in bs.find_all('description'):
        descriptions.append(el.text)
        
    claims = []
    for el in bs.find_all('claim'):
        claims.append(el.text)
    
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
        for classification in classifications:
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


filename = "ipa200109.xml"

xml_text = html.unescape(open(filename, 'r').read())

count = 1
success, errors = [], []
for patent in xml_text.split("<?xml version=\"1.0\" encoding=\"UTF-8\"?>"):

    if patent is None or patent == "":
        continue
    
    bs = BeautifulSoup(patent)
    
    application = bs.find('us-patent-application')
    title = "None"
    
    try:
        title = application.find('invention-title').text
    except Exception as e:
        print(e)

    try:
        parse_uspto_file(application)
        success.append(title)
    except Exception as e:
        exception_tuple = (count, title, e)
        errors.append(exception_tuple)
       
    if (len(success)+len(errors)) % 70 == 0:
        print(count, title)        
    count += 1


print("Errors")
for e in errors:
    print(e)
    
print("Success Count:", len(success))
print("Error Count:", len(errors))
