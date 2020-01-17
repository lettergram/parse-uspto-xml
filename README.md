Parse USPTO
===========

Steps:

*Step 1*: Download XML patents: https://bulkdata.uspto.gov/

Download under the header:

```
Patent Application Full Text Data (No Images) (MAR 15, 2001 - PRESENT)
Contains the full text of each patent application (non-provisional utility and plant) published weekly (Thursdays) from March 15, 2001 to present (excludes images/drawings). Subset of the Patent Application Full Text Data with Embedded TIFF Images.
```

*Step 2*: Extract the ziped files


*Step 3*: Split the XML files into individual patents:

```bash
mkdir <foldername>
csplit -f '<foldername>/patent-' -b '%02d.xml' <filename>.xml '/^<?xml /' '{*}'`
```

This wills plit the file into their individual patents.

Recommend setting foldername to the date of the patent, e.g.: `2002-01-01/`

This was taken from: https://stackoverflow.com/questions/55885078/parsing-uspto-xml-files

Step 4: Individual patents can then be parsed with:

```python
parse_patent.py
```