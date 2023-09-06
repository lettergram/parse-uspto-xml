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

**Step 2**: Extract the zipped file: `*.xml`

**Step 3**: Install the package locally with:

```
pip install -e .
```

**Step 4**: Individual patents (or directories) can then be parsed with:

```
python parse_uspto_xml/parse_patent.py <filename.xml> <filename.xml> <directory>
```

You can edit the `filename` variable in the python file `parse_patent.py` to match the unzipped file. Inside that file are typically thousands of patents which can be parsed for the given week.

Using the `parse_patent.py` if you add it will load all the  .xml files.

## Download all Files

For 2005 to Today, you can download all the zip files for a given year using the following format:

```
wget -r -np -l1 -nd -A zip https://bulkdata.uspto.gov/data/patent/grant/redbook/fulltext/<year>/
```

This will download all the `.zip` files off that page, which contain all the patents for the given year (as a zipped `.xml` file).

If the `-nd` command is dropped, a directory will be created in the form:

```
bulkdata.uspto.gov/data/patent/grant/redbook/fulltext/<year>/<filename>.zip`
```

It's recommended, to create a folder such as: `patent/<year>`, then execute the command to download all the `.zip` files.

When all the files are downloaded it's possible to unzip all the directory with:
```
unzip \*.zip
```

## Storing in Database

In addition, it's possible to save the parsed data in a database. In this repository, we provide documentation in [config/README](config/README.md) to configure PostgreSQL to store and search the patents.

This reduces the size of a file `ipa200109.xml` of *734MB* to *154MB* (in the database).

In terms of overall size, the XML files are 367Gb, the parsed files (in the database) are

In terms of decompressed data (by year) & unerrored parsed patent documents:

* 2005 - 11Gb - 157,822
* 2006 - 15Gb - 196,485
* 2007 - 14Gb - 182,968
* 2008 - 14Gb - 185,249
* 2009 - 16Gb - 192,045
* 2010 - 20Gb - 244,589
* 2011 - 21Gb - 248,091
* 2012 - 24Gb - 277,264
* 2013 - 28Gb - 303,641
* 2014 - 31Gb - 327,014
* 2015 - 32Gb - 326,969
* 2016 - 33Gb - 334,674
* 2017 - 36Gb - 352,547
* 2018 - 35Gb - 341,104
* 2019 - 42Gb - 392,618

Get patent count by year (in PostgreSQL):

```
SELECT date_trunc('year', publication_date), count(*) from uspto_patents group by date_trunc('year', publication_date) ORDER BY date_trunc('year', publication_date);
```
