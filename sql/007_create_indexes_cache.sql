CREATE INDEX IF NOT EXISTS
idx_fact_sales_invoice_date
ON warehouse.fact_sales(invoice_date);


CREATE INDEX IF NOT EXISTS
idx_fact_sales_country_date
ON warehouse.fact_sales(
    country_key,
    invoice_date
);


CREATE INDEX IF NOT EXISTS
idx_fact_sales_customer_date
ON warehouse.fact_sales(
    customer_key,
    invoice_date DESC
);


CREATE INDEX IF NOT EXISTS
idx_fact_sales_product_date
ON warehouse.fact_sales(
    product_key,
    invoice_date DESC
);


CREATE INDEX IF NOT EXISTS
idx_fact_sales_invoice_no
ON warehouse.fact_sales(invoice_no);


CREATE MATERIALIZED VIEW IF NOT EXISTS
reporting.monthly_sales_summary
AS
SELECT
    date_trunc(
        'month',
        invoice_date
    )::DATE AS sales_month,

    country_key,

    SUM(quantity)::BIGINT
        AS net_quantity,

    SUM(line_amount)::NUMERIC(24, 2)
        AS net_revenue,

    COUNT(*)::BIGINT
        AS transaction_lines,

    COUNT(*) FILTER (
        WHERE is_cancellation
    )::BIGINT
        AS cancellation_lines,

    COUNT(
        DISTINCT customer_key
    ) FILTER (
        WHERE customer_key <> 0
    )::BIGINT
        AS known_customers

FROM warehouse.fact_sales

GROUP BY
    sales_month,
    country_key

WITH NO DATA;


CREATE UNIQUE INDEX IF NOT EXISTS
idx_monthly_sales_summary
ON reporting.monthly_sales_summary(
    sales_month,
    country_key
);


CREATE OR REPLACE VIEW
reporting.v_monthly_sales_by_country
AS
SELECT
    summary.sales_month,
    country.country_name,
    summary.net_quantity,
    summary.net_revenue,
    summary.transaction_lines,
    summary.cancellation_lines,
    summary.known_customers

FROM reporting.monthly_sales_summary
    AS summary

JOIN warehouse.dim_country
    AS country

    ON country.country_key
        = summary.country_key;