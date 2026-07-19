# Performance Optimization

## Partitioning

The fact table is partitioned monthly by `invoice_date`.

Partitioning is implemented to demonstrate scalable date-based maintenance and partition pruning. At approximately 536,000 rows, it may not improve every query.

## Indexes

Indexes support:

- invoice lookup;
- date filtering;
- country/date reporting;
- customer history;
- product performance.

## Query plans

The benchmark runs `EXPLAIN (ANALYZE, BUFFERS)` and writes the results to `reports/performance_report.md`.

Exact timings vary by computer and cache state.

## Caching

`reporting.monthly_sales_summary` is a materialized view containing 314 month-country combinations.

It reduces repeated monthly reporting from more than 536,000 fact rows to 314 cached rows.

The view is refreshed after a successful pipeline run.