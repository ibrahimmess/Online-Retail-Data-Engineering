ALTER TABLE audit.metadata_repository
ADD COLUMN IF NOT EXISTS storage_location TEXT;


UPDATE audit.metadata_repository
SET storage_location =
    'PostgreSQL: '
    || target_schema
    || '.'
    || target_table
WHERE storage_location IS NULL;


INSERT INTO audit.metadata_repository (
    source_system,
    source_column,
    transformation_rule,
    target_schema,
    target_table,
    target_column,
    data_type,
    nullable,
    business_definition,
    storage_location
)
SELECT
    CASE
        WHEN column_info.table_schema = 'raw'
        THEN 'Online Retail CSV'
        ELSE 'Internal ETL pipeline'
    END,

    CASE
        WHEN column_info.table_schema = 'raw'
        THEN column_info.column_name
        ELSE NULL
    END,

    CASE
        WHEN column_info.table_schema = 'raw'
        THEN 'Loaded without business transformation'
        WHEN column_info.table_schema = 'staging'
        THEN 'Cleaned, standardized, typed, and validated'
        WHEN column_info.table_schema = 'warehouse'
        THEN 'Loaded from staging into dimensional model'
        WHEN column_info.table_schema = 'reporting'
        THEN 'Derived reporting or cache object'
        ELSE 'Generated or maintained by ETL auditing'
    END,

    column_info.table_schema,
    column_info.table_name,
    column_info.column_name,

    CASE
        WHEN column_info.character_maximum_length IS NOT NULL
        THEN
            column_info.data_type
            || '('
            || column_info.character_maximum_length
            || ')'
        WHEN column_info.numeric_precision IS NOT NULL
            AND column_info.numeric_scale IS NOT NULL
        THEN
            column_info.data_type
            || '('
            || column_info.numeric_precision
            || ','
            || column_info.numeric_scale
            || ')'
        ELSE column_info.data_type
    END,

    column_info.is_nullable = 'YES',

    'Physical metadata for '
    || column_info.table_schema
    || '.'
    || column_info.table_name
    || '.'
    || column_info.column_name,

    'PostgreSQL: '
    || column_info.table_schema
    || '.'
    || column_info.table_name

FROM information_schema.columns
    AS column_info

WHERE column_info.table_schema IN (
    'raw',
    'staging',
    'warehouse',
    'audit',
    'reporting'
)
AND NOT (
    column_info.table_schema = 'audit'
    AND column_info.table_name = 'metadata_repository'
)

ON CONFLICT (
    target_schema,
    target_table,
    target_column
)
DO UPDATE SET
    data_type = EXCLUDED.data_type,
    nullable = EXCLUDED.nullable,
    storage_location = EXCLUDED.storage_location,
    updated_at = CURRENT_TIMESTAMP;
