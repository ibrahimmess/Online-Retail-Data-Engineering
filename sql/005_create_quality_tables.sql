CREATE TABLE IF NOT EXISTS
audit.data_quality_results (
    result_id BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    run_id UUID NOT NULL
        REFERENCES audit.etl_runs(run_id),

    check_name TEXT NOT NULL,
    quality_dimension TEXT NOT NULL,

    severity TEXT NOT NULL CHECK (
        severity IN (
            'WARNING',
            'CRITICAL'
        )
    ),

    status TEXT NOT NULL CHECK (
        status IN (
            'PASS',
            'WARN',
            'FAIL'
        )
    ),

    observed_value DOUBLE PRECISION,

    expected_rule TEXT NOT NULL,

    details JSONB NOT NULL
        DEFAULT '{}'::JSONB,

    checked_at TIMESTAMPTZ NOT NULL
        DEFAULT CURRENT_TIMESTAMP
);