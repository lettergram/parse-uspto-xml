Database Management
===================

This document provides a guide on how to setup / configure a PostgreSQL database to manage patents being parsed.

### PostgreSQL Configuration

This application currently requires postgreSQL to function, below is a method for creating the database and user such that it will be able to use the appropriate functionality. Note, the commands must be ran from a postgreSQL user who has a superuser privilege.

**Create Role**
```
CREATE ROLE patent_manager WITH LOGIN PASSWORD 'enter password here.';
```

**Login as User**
```
psql -d uspto_patents -U patent_manager;
```

**Create Database**
```
CREATE DATABASE uspto_patents;

GRANT ALL PRIVILEGES ON DATABASE uspto_patents TO patent_manager;
```

**Create table**
```
CREATE TABLE uspto_patents(
       publication_number VARCHAR,
       publication_title VARCHAR,
       publication_date DATE,
       publication_type VARCHAR,
       authors VARCHAR,
       sections VARCHAR,
       section_classes VARCHAR,
       section_class_subclasses VARCHAR,
       section_class_subclass_groups VARCHAR,
       abstract TEXT,
       description TEXT,
       claims TEXT,
       created_at TIMESTAMP without time zone,
       updated_at TIMESTAMP without time zone,
       PRIMARY KEY(publication_number)
);
```

At this point the script(s) in this repository will work. However, if we wish to search the table, we should add indexes:

**Create indexes to improve search speeds**
```
CREATE INDEX idx_publication_date ON uspto_patents (publication_date);
CREATE INDEX idx_publication_title ON uspto_patents ((lower(publication_title)));
```

**Optional indexes to improve search speeds (text searches)**
```
CREATE INDEX idx_sections ON uspto_patents USING GIN (sections);
CREATE INDEX idx_section_classes ON uspto_patents USING GIN (section_classes);
CREATE INDEX idx_section_class_subclasses ON uspto_patents USING GIN (section_class_subclasses);
CREATE INDEX idx_section_class_subclass_groups ON uspto_patents USING GIN (section_class_subclass_groups);
```

**Database Size**

To check the database size. This is useful to ensure the entire disk is not filled while parsing the data, as there are terabytes of patent data.

```
SELECT pg_size_pretty(pg_database_size('uspto_patents'));
```

### Environment Setup

**PostgreSQL Database**

    * DATABASE_HOSTNAME - Hostname the instance
    * DATABASE_NAME - Name of the database
    * DATABASE_USERNAME - Username for database
    * DATABASE_PASSWORD - Password for database
    * DATABASE_PORT - Port to access database