CREATE OR REPLACE FUNCTION
warehouse.load_batch(p_batch_id UUID)
RETURNS BIGINT
LANGUAGE plpgsql
AS $$
DECLARE
    inserted_fact_rows BIGINT := 0;
BEGIN
    INSERT INTO warehouse.dim_date (
        date_key,
        full_date,
        day_of_month,
        month_number,
        month_name,
        quarter_number,
        year_number,
        iso_day_of_week,
        day_name,
        is_weekend
    )
    SELECT
        to_char(
            calendar_date,
            'YYYYMMDD'
        )::INTEGER,

        calendar_date,

        EXTRACT(
            DAY FROM calendar_date
        )::SMALLINT,

        EXTRACT(
            MONTH FROM calendar_date
        )::SMALLINT,

        trim(
            to_char(
                calendar_date,
                'Month'
            )
        ),

        EXTRACT(
            QUARTER FROM calendar_date
        )::SMALLINT,

        EXTRACT(
            YEAR FROM calendar_date
        )::SMALLINT,

        EXTRACT(
            ISODOW FROM calendar_date
        )::SMALLINT,

        trim(
            to_char(
                calendar_date,
                'Day'
            )
        ),

        EXTRACT(
            ISODOW FROM calendar_date
        ) IN (6, 7)

    FROM (
        SELECT generate_series(
            MIN(invoice_date),
            MAX(invoice_date),
            INTERVAL '1 day'
        )::DATE AS calendar_date

        FROM staging.online_retail_clean

        WHERE batch_id = p_batch_id
    ) AS calendar

    ON CONFLICT (date_key) DO NOTHING;


    WITH description_counts AS (
        SELECT
            stock_code,
            description,
            product_type,
            COUNT(*) AS frequency,
            MIN(invoice_timestamp)
                AS first_seen_at,
            MAX(invoice_timestamp)
                AS last_seen_at

        FROM staging.online_retail_clean

        WHERE batch_id = p_batch_id

        GROUP BY
            stock_code,
            description,
            product_type
    ),

    ranked_descriptions AS (
        SELECT
            *,

            ROW_NUMBER() OVER (
                PARTITION BY stock_code

                ORDER BY
                    (
                        description
                        = 'UNKNOWN PRODUCT'
                    ) ASC,

                    frequency DESC,
                    last_seen_at DESC,
                    description ASC
            ) AS description_rank

        FROM description_counts
    )

    INSERT INTO warehouse.dim_product (
        stock_code,
        description,
        product_type,
        first_seen_at,
        last_seen_at
    )

    SELECT
        stock_code,
        description,
        product_type,
        first_seen_at,
        last_seen_at

    FROM ranked_descriptions

    WHERE description_rank = 1

    ON CONFLICT (stock_code)
    DO UPDATE SET
        description =
            CASE
                WHEN
                    EXCLUDED.description
                    = 'UNKNOWN PRODUCT'
                THEN
                    warehouse.dim_product
                        .description
                ELSE
                    EXCLUDED.description
            END,

        product_type =
            EXCLUDED.product_type,

        first_seen_at =
            LEAST(
                warehouse.dim_product
                    .first_seen_at,
                EXCLUDED.first_seen_at
            ),

        last_seen_at =
            GREATEST(
                warehouse.dim_product
                    .last_seen_at,
                EXCLUDED.last_seen_at
            ),

        is_active = TRUE,

        updated_at = CURRENT_TIMESTAMP;


    INSERT INTO warehouse.dim_customer (
        customer_id,
        is_unknown,
        first_seen_at,
        last_seen_at
    )

    SELECT
        customer_id,
        FALSE,
        MIN(invoice_timestamp),
        MAX(invoice_timestamp)

    FROM staging.online_retail_clean

    WHERE
        batch_id = p_batch_id
        AND customer_id IS NOT NULL

    GROUP BY customer_id

    ON CONFLICT (customer_id)
    DO UPDATE SET
        first_seen_at =
            LEAST(
                warehouse.dim_customer
                    .first_seen_at,
                EXCLUDED.first_seen_at
            ),

        last_seen_at =
            GREATEST(
                warehouse.dim_customer
                    .last_seen_at,
                EXCLUDED.last_seen_at
            ),

        updated_at = CURRENT_TIMESTAMP;


    INSERT INTO warehouse.dim_country (
        country_name,
        is_unknown
    )

    SELECT DISTINCT
        country,
        FALSE

    FROM staging.online_retail_clean

    WHERE batch_id = p_batch_id

    ON CONFLICT (country_name)
    DO UPDATE SET
        updated_at = CURRENT_TIMESTAMP;


    INSERT INTO warehouse.fact_sales (
        invoice_date,
        invoice_timestamp,
        date_key,
        product_key,
        customer_key,
        country_key,
        invoice_no,
        source_row_number,
        quantity,
        unit_price,
        transaction_type,
        is_cancellation,
        is_zero_price,
        is_quantity_outlier,
        is_price_outlier,
        source_batch_id,
        source_row_hash
    )

    SELECT
        source.invoice_date,
        source.invoice_timestamp,

        to_char(
            source.invoice_date,
            'YYYYMMDD'
        )::INTEGER,

        product.product_key,

        COALESCE(
            customer.customer_key,
            0
        ),

        country.country_key,

        source.invoice_no,
        source.source_row_number,
        source.quantity,
        source.unit_price,
        source.transaction_type,
        source.is_cancellation,
        source.is_zero_price,
        source.is_quantity_outlier,
        source.is_price_outlier,
        source.batch_id,
        source.source_row_hash

    FROM staging.online_retail_clean
        AS source

    JOIN warehouse.dim_product
        AS product
        ON product.stock_code
            = source.stock_code

    LEFT JOIN warehouse.dim_customer
        AS customer
        ON customer.customer_id
            = source.customer_id

    JOIN warehouse.dim_country
        AS country
        ON country.country_name
            = source.country

    WHERE source.batch_id = p_batch_id

    ON CONFLICT (
        invoice_date,
        source_row_hash
    )
    DO NOTHING;


    GET DIAGNOSTICS
        inserted_fact_rows = ROW_COUNT;

    RETURN inserted_fact_rows;
END;
$$;