ALTER TABLE audit.etl_runs
ALTER COLUMN batch_id DROP NOT NULL;


ALTER TABLE audit.etl_runs
ADD COLUMN IF NOT EXISTS current_stage TEXT;


ALTER TABLE audit.etl_runs
ADD COLUMN IF NOT EXISTS fact_rows_reconciled BIGINT;
