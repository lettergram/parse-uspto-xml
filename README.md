Parse USPTO
===========

Steps:

*Step 1*: Download XML patents: https://bulkdata.uspto.gov/

Download under the header:

```
Patent Application Full Text Data (No Images) (MAR 15, 2001 - PRESENT)
Contains the full text of each patent application (non-provisional utility and plant) published weekly (Thursdays) from March 15, 2001 to present (excludes images/drawings). Subset of the Patent Application Full Text Data with Embedded TIFF Images.
```

*Step 2*: Extract the ziped file: `*.xml`

*Step 3*: Individual patents can then be parsed with:

```python
parse_patent.py
```

You can edit the `filename` variable in the python file `parse_patent.py` to match the unzipped file. Inside that file are typically thousands of patents which can be parsed for the given week.