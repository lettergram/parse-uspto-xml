import os 
import html
from bs4 import BeautifulSoup

test_filename = '2007/patent-4002.xml'
directory = '2007'

def parse_uspto_file(filename):
    
    xml_text = html.unescape(open(filename, 'r').read())

    count = 1
    """
    for line in xml_text.split("\n"):    
        print(count, line)
        count += 1
    """
    
    bs = BeautifulSoup(xml_text)

    print(bs.prettify())
    print("Filename:", filename)
    print("\n\n")
    print("\n--------------------------------------------------------\n")

    publication_title = bs.find('invention-title').text
    print("USPTO Invention Title:", publication_title)

    publication_num = bs.find('us-patent-application')['file'].split("-")[0]
    print("USPTO Publication Number:", publication_num)

    publication_date = bs.find('publication-reference').find('date').text
    print("USPTO Publication Date:", publication_date)

    application_type = bs.find('application-reference')['appl-type']
    print("USPTO Application Type:", application_type)
    
    count = 1
    for classes in bs.find_all('classifications-ipcr'):
        for el in classes.find_all('classification-ipcr'):        
            classification  = el.find('section').text
            classification += el.find('class').text
            classification += el.find('subclass').text
            print("USPTO Classification #"+str(count)+":", classification)        
            count += 1
        
    print("\n")
        
    count = 1
    for parties in bs.find_all('parties'):
        for applicants in parties.find_all('applicants'):
            for el in applicants.find_all('addressbook'):
                first_name = el.find('first-name').text
                last_name = el.find('last-name').text
                print("Inventor #"+str(count)+":", first_name, last_name)
                count += 1

    print("\n--------------------------------------------------------\n")
    
    for el in bs.find_all('abstract'):
        print("Abstract:", el.text)

    for el in bs.find_all('description'):
        print("Description:", el.text)

    for el in bs.find_all('claim'):
        print(el.text)



errors = []
for filename in os.listdir(directory):
    if filename.endswith('.xml'):
        try:
            parse_uspto_file(directory + "/" + filename)
        except Exception as e:
            errors.append(e)

print("Errors")
for e in errors:
    print(e)
print("Error Count:", len(e))
