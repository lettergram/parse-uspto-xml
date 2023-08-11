DATABASE_PASS='enter password here.'
DATABASE_USER='patent_manager'
DATABASE_NAME='uspto_patents'

psql -c "CREATE ROLE $DATABASE_USER WITH LOGIN PASSWORD '$DATABASE_PASS';"
psql -c "CREATE DATABASE $DATABASE_NAME;"
psql -d $DATABASE_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;"


psql -X -U $DATABASE_USER password='$DATABASE_PASS' -d $DATABASE_NAME << PSQL
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

CREATE INDEX idx_publication_date ON uspto_patents (publication_date);
CREATE INDEX idx_publication_title ON uspto_patents ((lower(publication_title)));


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

CREATE TABLE uspto_referential_documents(
   id SERIAL PRIMARY KEY,
   uspto_publication_number VARCHAR REFERENCES uspto_patents (publication_number),
   reference VARCHAR,
   document_type reference_document_types,
   cited_by_examiner BOOLEAN,
   country VARCHAR,
   metadata jsonb,
   created_at TIMESTAMP without time zone,
   updated_at TIMESTAMP without time zone,
   CONSTRAINT patent_reference UNIQUE (uspto_publication_number, reference, document_type)
);

CREATE INDEX uspto_publication_number ON uspto_referential_documents (uspto_publication_number);

PSQL
