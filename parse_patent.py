import xml.etree.ElementTree as etree
filename = '20020101/patent-1888.xml'
xml_file = open(filename, 'r')
xml_tree = etree.parse(xml_file.read())
