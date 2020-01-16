Parse USPTO
===========

Steps:

*Step 1*: Download XML patents: https://bulkdata.uspto.gov/
*Step 2*: Extract the ziped files
*Step 3*: Split the XML files into individual patents:

```bash
csplit -f 'patent-' -b '%02d.xml' <filename>.xml '/^<?xml /' '{*}'`
```

This wills plit the file into their individual patents.

This was taken from: https://stackoverflow.com/questions/55885078/parsing-uspto-xml-files

Step 4: Individual patents can then be parsed with:

```python
parse_patent.py
```