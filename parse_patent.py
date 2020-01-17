import xml.etree.ElementTree as etree
import html

test_str = "<NAM><ONM><STEXT><PDAT>Oblon, Spivak, McClelland, Maier & Neustadt, P.C.</PDAT></STEXT></ONM></NAM>"

test_str = test_str.replace("&", "and")
print(test_str)

xml_tree = etree.fromstring(test_str, etree.XMLParser(encoding='utf-8'))
print(xml_tree)



filename = '2007/patent-6296.xml'

xml_text = html.unescape(open(filename, 'r').read())

print(type(xml_text))
count = 1
for line in xml_text.split("\n"):
    
    print(count, line)
    count += 1


xml_tree = etree.fromstring(xml_text, etree.XMLParser(encoding='utf-8'))
print(xml_tree)

for child in xml_tree.findall('us-patent-application'):
    print(child.attrib)

