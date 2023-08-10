DB_PASSWORD='enter password here.'
DB_USER='patent_manager'
DB_NAME='uspto_patents'

psql -c "CREATE ROLE $DB_USER WITH LOGIN PASSWORD '$DB_PASSWORD';"
psql -c "CREATE DATABASE $DB_NAME;"
psql -d $DB_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"


RUN_ON_MYDB="psql -X -U $DB_USER password='$DB_PASSWORD' -d $DB_NAME --set ON_ERROR_STOP=on"

psql -X -U $DB_USER password='$DB_PASSWORD' -d $DB_NAME --set ON_ERROR_STOP=on << PSQL
CREATE TABLE uspto_patents(
       publication_number VARCHAR,
       publication_title VARCHAR,
       publication_date DATE,
       publication_type VARCHAR,
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


CREATE reference_document_types AS ENUM (
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
   document_type TEXT,
   country VARCHAR,
   metadata jsonb,
   created_at TIMESTAMP without time zone,
   updated_at TIMESTAMP without time zone,
   CONSTRAINT patent_reference UNIQUE (uspto_publication_number, reference)
);

CREATE INDEX uspto_publication_number ON uspto_referential_documents (uspto_publication_number);

PSQL
