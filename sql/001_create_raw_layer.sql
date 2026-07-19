CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS raw;


CREATE TABLE IF NOT EXISTS audit.source_files (
    batch_id UUID PRIMARY KEY,

    source_file_name TEXT NOT NULL,
    source_file_path TEXT NOT NULL,

    sha256 CHAR(64) NOT NULL UNIQUE,
    file_size_bytes BIGINT NOT NULL,

    row_count BIGINT,

    status TEXT NOT NULL CHECK (
        status IN (
            'REGISTERED',
            'RAW_LOADED',
            'FAILED'
        )
    ),

    registered_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    updated_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS raw.online_retail (
    batch_id UUID NOT NULL
        REFERENCES audit.source_files(batch_id),

    source_row_number BIGINT NOT NULL,

    invoice_no TEXT,
    stock_code TEXT,
    description TEXT,
    quantity TEXT,
    invoice_date TEXT,
    unit_price TEXT,
    customer_id TEXT,
    country TEXT,

    ingested_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (
        batch_id,
        source_row_number
    )
);


CREATE INDEX IF NOT EXISTS idx_raw_online_retail_batch
    ON raw.online_retail(batch_id);