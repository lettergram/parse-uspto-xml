import xml.etree.ElementTree as etree
import html

test_str = "<NAM><ONM><STEXT><PDAT>Oblon, Spivak, McClelland, Maier & Neustadt, P.C.</PDAT></STEXT></ONM></NAM>"

test_str = test_str.replace("&", "and")
print(test_str)

xml_tree = etree.fromstring(test_str, etree.XMLParser(encoding='utf-8'))
print(xml_tree)



filename = '20020101/patent-1888.xml'

xml_text = html.unescape(open(filename, 'r').read())
xml_text = xml_text.replace("&", "and")
xml_text = xml_text.replace("+", "")

print(type(xml_text))
count = 1
for line in xml_text.split("\n"):
    
    print(count, line)
    count += 1
    if count == 371:
        subcount = 0
        for char in line:
            subcount += 1
            if subcount > 820 and subcount < 850:
                print(subcount, char)
        break


xml_tree = etree.fromstring(xml_text, etree.XMLParser(encoding='utf-8'))
print(xml_tree)
