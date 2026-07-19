# Query Performance Report

Generated at: 2026-07-19T21:34:48.526231+00:00

Timings depend on hardware. The execution-plan shape is the primary evidence.

## Invoice lookup

Execution time: 1.722 ms

```text
Append  (cost=0.29..159.78 rows=189 width=25) (actual time=0.208..1.613 rows=7 loops=1)
  Buffers: shared hit=1 read=26
  ->  Index Scan using fact_sales_2010_12_invoice_no_idx on fact_sales_2010_12 fact_sales_1  (cost=0.29..11.09 rows=13 width=25) (actual time=0.207..0.209 rows=7 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared hit=1 read=2
  ->  Index Scan using fact_sales_2011_01_invoice_no_idx on fact_sales_2011_01 fact_sales_2  (cost=0.29..12.47 rows=14 width=25) (actual time=0.046..0.047 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_02_invoice_no_idx on fact_sales_2011_02 fact_sales_3  (cost=0.29..12.17 rows=13 width=25) (actual time=0.118..0.118 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_03_invoice_no_idx on fact_sales_2011_03 fact_sales_4  (cost=0.29..12.24 rows=14 width=25) (actual time=0.299..0.299 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_04_invoice_no_idx on fact_sales_2011_04 fact_sales_5  (cost=0.29..11.84 rows=12 width=25) (actual time=0.051..0.051 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_05_invoice_no_idx on fact_sales_2011_05 fact_sales_6  (cost=0.29..11.39 rows=13 width=25) (actual time=0.112..0.112 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_06_invoice_no_idx on fact_sales_2011_06 fact_sales_7  (cost=0.29..11.89 rows=13 width=25) (actual time=0.043..0.043 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_07_invoice_no_idx on fact_sales_2011_07 fact_sales_8  (cost=0.29..12.15 rows=14 width=25) (actual time=0.034..0.035 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_08_invoice_no_idx on fact_sales_2011_08 fact_sales_9  (cost=0.29..12.17 rows=14 width=25) (actual time=0.064..0.065 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_09_invoice_no_idx on fact_sales_2011_09 fact_sales_10  (cost=0.29..11.92 rows=17 width=25) (actual time=0.048..0.049 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_10_invoice_no_idx on fact_sales_2011_10 fact_sales_11  (cost=0.29..15.20 rows=19 width=25) (actual time=0.146..0.147 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_11_invoice_no_idx on fact_sales_2011_11 fact_sales_12  (cost=0.29..12.80 rows=20 width=25) (actual time=0.154..0.155 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_12_invoice_no_idx on fact_sales_2011_12 fact_sales_13  (cost=0.29..11.49 rows=12 width=25) (actual time=0.239..0.240 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Seq Scan on fact_sales_default fact_sales_14  (cost=0.00..0.00 rows=1 width=64) (actual time=0.019..0.020 rows=0 loops=1)
        Filter: (invoice_no = '536365'::text)
Planning:
  Buffers: shared hit=447
Planning Time: 2.755 ms
Execution Time: 1.722 ms
```

## November partition query

Execution time: 23.487 ms

```text
HashAggregate  (cost=3921.86..3922.32 rows=37 width=40) (actual time=23.461..23.467 rows=24 loops=1)
  Group Key: fact_sales.country_key
  Batches: 1  Memory Usage: 32kB
  Buffers: shared hit=2255
  ->  Seq Scan on fact_sales_2011_11 fact_sales  (cost=0.00..3505.14 rows=83343 width=14) (actual time=0.005..12.211 rows=83343 loops=1)
        Filter: ((invoice_date >= '2011-11-01'::date) AND (invoice_date < '2011-12-01'::date))
        Buffers: shared hit=2255
Planning:
  Buffers: shared hit=74
Planning Time: 0.252 ms
Execution Time: 23.487 ms
```

## Base fact aggregation

Execution time: 516.888 ms

```text
Sort  (cost=27542.91..27571.12 rows=11285 width=44) (actual time=507.423..516.674 rows=314 loops=1)
  Sort Key: ((date_trunc('month'::text, (fact_sales.invoice_date)::timestamp with time zone))::date), fact_sales.country_key
  Sort Method: quicksort  Memory: 40kB
  Buffers: shared hit=12105 read=2425
  ->  Finalize HashAggregate  (cost=26557.61..26783.31 rows=11285 width=44) (actual time=505.830..515.873 rows=314 loops=1)
        Group Key: ((date_trunc('month'::text, (fact_sales.invoice_date)::timestamp with time zone))::date), fact_sales.country_key
        Batches: 1  Memory Usage: 529kB
        Buffers: shared hit=12105 read=2425
        ->  Gather  (cost=23849.21..26331.91 rows=22570 width=44) (actual time=503.745..513.694 rows=347 loops=1)
              Workers Planned: 2
              Workers Launched: 2
              Buffers: shared hit=12105 read=2425
              ->  Partial HashAggregate  (cost=22849.21..23074.91 rows=11285 width=44) (actual time=500.728..501.201 rows=116 loops=3)
                    Group Key: ((date_trunc('month'::text, (fact_sales.invoice_date)::timestamp with time zone))::date), fact_sales.country_key
                    Batches: 1  Memory Usage: 465kB
                    Buffers: shared hit=12105 read=2425
                    Worker 0:  Batches: 1  Memory Usage: 465kB
                    Worker 1:  Batches: 1  Memory Usage: 465kB
                    ->  Parallel Append  (cost=0.00..21172.22 rows=223598 width=18) (actual time=0.012..348.059 rows=178880 loops=3)
                          Buffers: shared hit=12105 read=2425
                          ->  Parallel Seq Scan on fact_sales_2011_11 fact_sales_12  (cost=0.00..3112.94 rows=49025 width=18) (actual time=0.010..99.969 rows=83343 loops=1)
                                Buffers: shared hit=2255
                          ->  Parallel Seq Scan on fact_sales_2011_10 fact_sales_11  (cost=0.00..2241.33 rows=35276 width=18) (actual time=0.010..55.813 rows=59969 loops=1)
                                Buffers: shared hit=1624
                          ->  Parallel Seq Scan on fact_sales_2011_09 fact_sales_10  (cost=0.00..1863.27 rows=29330 width=18) (actual time=0.131..107.234 rows=49861 loops=1)
                                Buffers: shared hit=598 read=752
                          ->  Parallel Seq Scan on fact_sales_2010_12 fact_sales_1  (cost=0.00..1569.16 rows=24695 width=18) (actual time=0.049..94.393 rows=41981 loops=1)
                                Buffers: shared hit=782 read=355
                          ->  Parallel Seq Scan on fact_sales_2011_07 fact_sales_8  (cost=0.00..1467.22 rows=23098 width=18) (actual time=0.053..80.234 rows=39267 loops=1)
                                Buffers: shared hit=911 read=152
                          ->  Parallel Seq Scan on fact_sales_2011_05 fact_sales_6  (cost=0.00..1374.63 rows=21636 width=18) (actual time=0.014..77.626 rows=36782 loops=1)
                                Buffers: shared hit=996
                          ->  Parallel Seq Scan on fact_sales_2011_06 fact_sales_7  (cost=0.00..1367.86 rows=21535 width=18) (actual time=0.025..28.048 rows=12203 loops=3)
                                Buffers: shared hit=991
                          ->  Parallel Seq Scan on fact_sales_2011_03 fact_sales_4  (cost=0.00..1362.11 rows=21435 width=18) (actual time=0.036..39.594 rows=18220 loops=2)
                                Buffers: shared hit=987
                          ->  Parallel Seq Scan on fact_sales_2011_08 fact_sales_9  (cost=0.00..1309.93 rows=20625 width=18) (actual time=0.011..65.621 rows=35062 loops=1)
                                Buffers: shared hit=769 read=180
                          ->  Parallel Seq Scan on fact_sales_2011_01 fact_sales_2  (cost=0.00..1304.26 rows=20529 width=18) (actual time=0.013..73.950 rows=34900 loops=1)
                                Buffers: shared hit=945
                          ->  Parallel Seq Scan on fact_sales_2011_04 fact_sales_5  (cost=0.00..1110.74 rows=17471 width=18) (actual time=0.028..72.919 rows=29701 loops=1)
                                Buffers: shared read=805
                          ->  Parallel Seq Scan on fact_sales_2011_02 fact_sales_3  (cost=0.00..1026.87 rows=16164 width=18) (actual time=0.004..11.707 rows=27479 loops=1)
                                Buffers: shared hit=563 read=181
                          ->  Parallel Seq Scan on fact_sales_2011_12 fact_sales_13  (cost=0.00..943.89 rows=14851 width=18) (actual time=0.015..8.194 rows=25246 loops=1)
                                Buffers: shared hit=684
                          ->  Parallel Seq Scan on fact_sales_default fact_sales_14  (cost=0.00..0.01 rows=1 width=18) (actual time=0.001..0.001 rows=0 loops=1)
Planning:
  Buffers: shared hit=125
Planning Time: 0.472 ms
Execution Time: 516.888 ms
```

## Materialized cache query

Execution time: 0.459 ms

```text
Sort  (cost=20.16..20.95 rows=314 width=19) (actual time=0.329..0.388 rows=314 loops=1)
  Sort Key: sales_month, country_key
  Sort Method: quicksort  Memory: 40kB
  Buffers: shared hit=4
  ->  Seq Scan on monthly_sales_summary  (cost=0.00..7.14 rows=314 width=19) (actual time=0.023..0.157 rows=314 loops=1)
        Buffers: shared hit=4
Planning:
  Buffers: shared hit=33 dirtied=1
Planning Time: 0.446 ms
Execution Time: 0.459 ms
```
