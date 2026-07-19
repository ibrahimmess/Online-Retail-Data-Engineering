CREATE SCHEMA IF NOT EXISTS staging;


ALTER TABLE audit.source_files
DROP CONSTRAINT IF EXISTS source_files_status_check;


ALTER TABLE audit.source_files
ADD CONSTRAINT source_files_status_check
CHECK (
    status IN (
        'REGISTERED',
        'RAW_LOADED',
        'TRANSFORMED',
        'WAREHOUSE_LOADED',
        'SUCCESS',
        'FAILED'
    )
);


CREATE TABLE IF NOT EXISTS audit.etl_runs (
    run_id UUID PRIMARY KEY,

    batch_id UUID
        REFERENCES audit.source_files(batch_id),

    status TEXT NOT NULL CHECK (
        status IN (
            'RUNNING',
            'SUCCESS',
            'FAILED'
        )
    ),

    current_stage TEXT,

    started_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    finished_at TIMESTAMPTZ,

    raw_rows BIGINT,
    accepted_rows BIGINT,
    rejected_rows BIGINT,
    duplicate_rows BIGINT,
    fact_rows_inserted BIGINT,
    fact_rows_reconciled BIGINT,

    warning_count INTEGER NOT NULL DEFAULT 0,

    error_message TEXT
);


CREATE TABLE IF NOT EXISTS audit.excluded_records (
    batch_id UUID NOT NULL
        REFERENCES audit.source_files(batch_id),

    source_row_number BIGINT NOT NULL,

    exclusion_type TEXT NOT NULL CHECK (
        exclusion_type IN (
            'REJECTED',
            'DUPLICATE'
        )
    ),

    reasons TEXT NOT NULL,

    raw_record JSONB NOT NULL,

    recorded_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        batch_id,
        source_row_number
    )
);


CREATE TABLE IF NOT EXISTS staging.online_retail_clean (
    batch_id UUID NOT NULL
        REFERENCES audit.source_files(batch_id),

    source_row_number BIGINT NOT NULL,

    invoice_no TEXT NOT NULL,
    stock_code TEXT NOT NULL,
    description TEXT NOT NULL,
    product_type TEXT NOT NULL,

    quantity INTEGER NOT NULL CHECK (
        quantity <> 0
    ),

    invoice_timestamp TIMESTAMP NOT NULL,
    invoice_date DATE NOT NULL,

    unit_price NUMERIC(18, 6) NOT NULL CHECK (
        unit_price >= 0
    ),

    customer_id TEXT,

    source_country TEXT NOT NULL,
    country TEXT NOT NULL,

    transaction_type TEXT NOT NULL,

    is_cancellation BOOLEAN NOT NULL,
    is_zero_price BOOLEAN NOT NULL,
    is_quantity_outlier BOOLEAN NOT NULL,
    is_price_outlier BOOLEAN NOT NULL,

    description_was_missing BOOLEAN NOT NULL,
    description_is_unknown BOOLEAN NOT NULL,

    source_row_hash CHAR(64) NOT NULL,

    transformed_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        batch_id,
        source_row_number
    ),

    UNIQUE (
        batch_id,
        source_row_hash
    )
);