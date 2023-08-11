DATABASE_PASS='enter password here.'
DATABASE_USER='patent_manager'
DATABASE_NAME='uspto_patents'

psql -c "CREATE ROLE $DATABASE_USER WITH LOGIN PASSWORD '$DATABASE_PASS';"
psql -c "CREATE DATABASE $DATABASE_NAME;"
psql -d $DATABASE_NAME -c "GRANT ALL PRIVILEGES ON DATABASE $DATABASE_NAME TO $DATABASE_USER;"


psql -h $DATABASE_HOST -p $DATABASE_PORT -U $DATABASE_USER password='$DATABASE_PASS' -d $DATABASE_NAME << PSQL
CREATE TABLE IF NOT EXISTS uspto_patents(
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

CREATE INDEX IF NOT EXISTS idx_publication_date ON uspto_patents (publication_date);
CREATE INDEX IF NOT EXISTS idx_publication_title ON uspto_patents ((lower(publication_title)));

DO \$\$
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
\$\$;

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

CREATE INDEX IF NOT EXISTS uspto_publication_number ON uspto_referential_documents (uspto_publication_number);

DO \$\$
BEGIN
    IF (select Substr(setting, 1, strpos(setting, '.')-1) from pg_settings where name = 'server_version')::INTEGER = 15 THEN
        --FOR PSQL >= 15 which allows null not distinct
        --CREATE UNIQUE INDEX IF NOT EXISTS patent_reference_constraint on uspto_referential_documents
        --    (uspto_publication_number, reference, document_type, country, (kind)) NULLS NOT DISTINCT;
        RAISE WARNING 'UNCOMMENT THIS SECTION FOR PSQL>=15; NO INDEXES APPLIED';
    ELSE
        --FOR PSQL < 15
        CREATE UNIQUE INDEX IF NOT EXISTS patent_reference_constraint_null on uspto_referential_documents
            (uspto_publication_number, COALESCE(reference, ''), document_type, COALESCE(country, ''), COALESCE(kind, ''));
    END IF;
END
\$\$;

PSQL
