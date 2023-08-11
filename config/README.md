Database Management
===================

This document provides a guide on how to setup / configure a PostgreSQL database to manage patents being parsed.

### PostgreSQL Configuration

This application currently requires postgreSQL to function, below is a method for creating the database and user such that it will be able to use the appropriate functionality. Note, the commands must be ran from a postgreSQL user who has a superuser privilege.

#### Script setup
Instead of manually setting up the databse, one can use the script `psql_setup_script.sh`.

First update the env vars at the top of the file:
```
DATABASE_PASS='enter password here.'
DATABASE_USER='patent_manager'
DATABASE_NAME='uspto_patents'
```

Then execute the script:
```console
chmod +x psql_setup_script.sh
./psql_setup_script.sh
```

#### Manual Setup

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
       grant_date DATE,
       application_num VARCHAR,
       application_date DATE,
       authors VARCHAR,
       organizations VARCHAR,
       attorneys VARCHAR,
       attorney_organizations VARCHAR,
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

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'reference_document_types') THEN
        CREATE TYPE reference_document_types AS ENUM (
            'continuation',
            'division',
            'continuation-in-part',
            'reissue',
            'substitution',
            'provisional',
            'prior',
            'priority-claim',
            'patent-reference',
            'other-reference'
        );
    END IF;
END
$$;

CREATE TABLE IF NOT EXISTS uspto_referential_documents(
   id SERIAL PRIMARY KEY,
   uspto_publication_number VARCHAR REFERENCES uspto_patents (publication_number),
   reference VARCHAR,
   document_type reference_document_types,
   cited_by_examiner BOOLEAN,
   country VARCHAR,
   kind VARCHAR,
   metadata jsonb,
   created_at TIMESTAMP without time zone,
   updated_at TIMESTAMP without time zone
);
```

At this point the script(s) in this repository will work. However, if we wish to search the table, we should add indexes:

**Create indexes to improve search speeds**
```
CREATE INDEX idx_publication_date ON uspto_patents (publication_date);
CREATE INDEX idx_publication_title ON uspto_patents ((lower(publication_title)));

CREATE INDEX IF NOT EXISTS uspto_publication_number ON uspto_referential_documents (uspto_publication_number);

DO $$
BEGIN
    IF (select Substr(setting, 1, strpos(setting, '.')-1) from pg_settings where name = 'server_version')::INTEGER = 15 THEN
        --FOR PSQL >= 15 which allows null not distinct
        --CREATE UNIQUE INDEX IF NOT EXISTS patent_reference_constraint on uspto_referential_documents
        --    (uspto_publication_number, reference, document_type, country, (metadata->>'kind')) NULLS NOT DISTINCT;
        RAISE WARNING "UNCOMMENT THIS SECTION FOR PSQL>=15; NO INDEXES APPLIED"
    ELSE
        --FOR PSQL < 15
        CREATE UNIQUE INDEX IF NOT EXISTS patent_reference_constraint_null on uspto_referential_documents
            (uspto_publication_number, COALESCE(reference, ''), document_type, COALESCE(country, ''), COALESCE(kind, ''));
    END IF;
END
$$;
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

    * DATABASE_HOST - Hostname the instance
    * DATABASE_NAME - Name of the database
    * DATABASE_USER - Username for database
    * DATABASE_PASS - Password for database
    * DATABASE_PORT - Port to access database
