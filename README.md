Parse USPTO
===========

**Step 1**: Download XML patents: https://bulkdata.uspto.gov/

Download under the header:

```
Patent Application Full Text Data (No Images) (MAR 15, 2001 - PRESENT)
Contains the full text of each patent application (non-provisional utility and plant)
published weekly (Thursdays) from March 15, 2001 to present (excludes images/drawings).
Subset of the Patent Application Full Text Data with Embedded TIFF Images.
```

The current script(s) only work on version 4.0 or higher of the XML (2005 - Present).

It also will skip all documents with DNA sequences.

**Step 2**: Extract the ziped file: `*.xml`

**Step 3**: Individual patents (or directories) can then be parsed with:

```python
parse_patent.py <filename.xml> <filename.xml> <directory>
```

You can edit the `filename` variable in the python file `parse_patent.py` to match the unzipped file. Inside that file are typically thousands of patents which can be parsed for the given week.

Using the `parse_patent.py` if you add a it will load all the  .xml files.

## Storing in Database

In addition, it's possible to save the parsed data in a database. In this repository, we provide documentation in [config/README](config/README.md) to configure PostgreSQL to store and search the patents.

This reduces the size of a file `ipa200109.xml` of *734MB* to *154MB* (in the database). 