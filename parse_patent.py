import os 
import html
from bs4 import BeautifulSoup

test_filename = '2007/patent-1951.xml'
directory = '2007'

def parse_uspto_file(filename, logging=False):
    
    xml_text = html.unescape(open(filename, 'r').read())

    count = 1
    """
    for line in xml_text.split("\n"):    
        print(count, line)
        count += 1
    """
    
    bs = BeautifulSoup(xml_text)
    
    publication_title = bs.find('invention-title').text
    publication_num = bs.find('us-patent-application')['file'].split("-")[0]
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


parse_uspto_file(test_filename, logging=True)

success = []
errors = []
file_count = len(os.listdir(directory))
for filename in os.listdir(directory):
    if filename.endswith('.xml'):
        try:
            parse_uspto_file(directory+"/"+filename)
            success.append(directory+"/"+filename)
        except Exception as e:
            errors.append((directory+"/"+filename, e))

        if (len(success)+len(errors)) % 10 == 0:
            print(
                "Total", len(success)+len(errors),
                "of", file_count,
                "-",
                "Success", len(success),
                "Errors", len(errors)
            )

print("Errors")
for e in errors:
    print(e)
    
print("Success Count:", len(success))
print("Error Count:", len(errors))
