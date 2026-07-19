CREATE SEQUENCE IF NOT EXISTS
audit.source_version_sequence;


ALTER TABLE audit.source_files
ADD COLUMN IF NOT EXISTS
source_version BIGINT;


UPDATE audit.source_files
SET source_version =
    nextval(
        'audit.source_version_sequence'
    )
WHERE source_version IS NULL;


ALTER TABLE audit.source_files
ALTER COLUMN source_version
SET DEFAULT nextval(
    'audit.source_version_sequence'
);


ALTER TABLE audit.source_files
ALTER COLUMN source_version
SET NOT NULL;


CREATE UNIQUE INDEX IF NOT EXISTS
idx_source_files_version
ON audit.source_files(source_version);


ALTER TABLE audit.source_files
ADD COLUMN IF NOT EXISTS
archived_path TEXT;


ALTER TABLE audit.source_files
ADD COLUMN IF NOT EXISTS
pipeline_version TEXT
DEFAULT '1.0.0';


CREATE TABLE IF NOT EXISTS
audit.metadata_repository (
    metadata_id BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    source_system TEXT NOT NULL,
    source_column TEXT,

    transformation_rule TEXT NOT NULL,

    target_schema TEXT NOT NULL,
    target_table TEXT NOT NULL,
    target_column TEXT NOT NULL,

    data_type TEXT NOT NULL,
    nullable BOOLEAN NOT NULL,

    business_definition TEXT NOT NULL,

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (
        target_schema,
        target_table,
        target_column
    )
);


INSERT INTO audit.metadata_repository (
    source_system,
    source_column,
    transformation_rule,
    target_schema,
    target_table,
    target_column,
    data_type,
    nullable,
    business_definition
)
VALUES
(
    'Online Retail CSV',
    'InvoiceNo',
    'Trim; C prefix indicates cancellation',
    'warehouse',
    'fact_sales',
    'invoice_no',
    'TEXT',
    FALSE,
    'Source invoice identifier'
),
(
    'Online Retail CSV',
    'StockCode',
    'Trim and uppercase; map to product key',
    'warehouse',
    'fact_sales',
    'product_key',
    'BIGINT',
    FALSE,
    'Product dimension foreign key'
),
(
    'Online Retail CSV',
    'Description',
    'Uppercase and recover by StockCode',
    'warehouse',
    'dim_product',
    'description',
    'TEXT',
    FALSE,
    'Canonical product description'
),
(
    'Online Retail CSV',
    'Quantity',
    'Parse integer; preserve signed returns',
    'warehouse',
    'fact_sales',
    'quantity',
    'INTEGER',
    FALSE,
    'Signed invoice-line quantity'
),
(
    'Online Retail CSV',
    'InvoiceDate',
    'Parse ISO timestamp',
    'warehouse',
    'fact_sales',
    'invoice_timestamp',
    'TIMESTAMP',
    FALSE,
    'Transaction timestamp'
),
(
    'Online Retail CSV',
    'UnitPrice',
    'Parse numeric; reject negative values',
    'warehouse',
    'fact_sales',
    'unit_price',
    'NUMERIC(18,6)',
    FALSE,
    'Price per item'
),
(
    'Online Retail CSV',
    'CustomerID',
    'Remove trailing .0; missing maps to key 0',
    'warehouse',
    'fact_sales',
    'customer_key',
    'BIGINT',
    FALSE,
    'Customer or UNKNOWN foreign key'
),
(
    'Online Retail CSV',
    'Country',
    'Trim; standardize EIRE and RSA',
    'warehouse',
    'fact_sales',
    'country_key',
    'BIGINT',
    FALSE,
    'Country dimension foreign key'
),
(
    'Derived',
    'Quantity * UnitPrice',
    'PostgreSQL generated column',
    'warehouse',
    'fact_sales',
    'line_amount',
    'NUMERIC(24,6)',
    FALSE,
    'Signed invoice-line value'
)
ON CONFLICT (
    target_schema,
    target_table,
    target_column
)
DO UPDATE SET
    transformation_rule =
        EXCLUDED.transformation_rule,

    business_definition =
        EXCLUDED.business_definition,

    updated_at =
        CURRENT_TIMESTAMP;