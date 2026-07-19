# Query Performance Report

Generated at: 2026-07-19T20:02:03.169332+00:00

Timings depend on hardware. The execution-plan shape is the primary evidence.

## Invoice lookup

Execution time: 1.196 ms

```text
Append  (cost=0.29..160.89 rows=190 width=25) (actual time=0.161..1.161 rows=7 loops=1)
  Buffers: shared hit=1 read=26
  ->  Index Scan using fact_sales_2010_12_invoice_no_idx on fact_sales_2010_12 fact_sales_1  (cost=0.29..11.01 rows=13 width=25) (actual time=0.161..0.163 rows=7 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared hit=1 read=2
  ->  Index Scan using fact_sales_2011_01_invoice_no_idx on fact_sales_2011_01 fact_sales_2  (cost=0.29..12.43 rows=14 width=25) (actual time=0.081..0.081 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_02_invoice_no_idx on fact_sales_2011_02 fact_sales_3  (cost=0.29..12.17 rows=13 width=25) (actual time=0.081..0.081 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_03_invoice_no_idx on fact_sales_2011_03 fact_sales_4  (cost=0.29..12.40 rows=14 width=25) (actual time=0.079..0.079 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_04_invoice_no_idx on fact_sales_2011_04 fact_sales_5  (cost=0.29..11.84 rows=12 width=25) (actual time=0.093..0.093 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_05_invoice_no_idx on fact_sales_2011_05 fact_sales_6  (cost=0.29..11.29 rows=13 width=25) (actual time=0.107..0.107 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_06_invoice_no_idx on fact_sales_2011_06 fact_sales_7  (cost=0.29..12.20 rows=14 width=25) (actual time=0.078..0.078 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_07_invoice_no_idx on fact_sales_2011_07 fact_sales_8  (cost=0.29..12.05 rows=14 width=25) (actual time=0.083..0.083 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_08_invoice_no_idx on fact_sales_2011_08 fact_sales_9  (cost=0.29..12.17 rows=14 width=25) (actual time=0.077..0.077 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_09_invoice_no_idx on fact_sales_2011_09 fact_sales_10  (cost=0.29..12.10 rows=17 width=25) (actual time=0.078..0.078 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_10_invoice_no_idx on fact_sales_2011_10 fact_sales_11  (cost=0.29..15.25 rows=19 width=25) (actual time=0.078..0.078 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_11_invoice_no_idx on fact_sales_2011_11 fact_sales_12  (cost=0.29..13.53 rows=20 width=25) (actual time=0.078..0.078 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Index Scan using fact_sales_2011_12_invoice_no_idx on fact_sales_2011_12 fact_sales_13  (cost=0.29..11.49 rows=12 width=25) (actual time=0.078..0.078 rows=0 loops=1)
        Index Cond: (invoice_no = '536365'::text)
        Buffers: shared read=2
  ->  Seq Scan on fact_sales_default fact_sales_14  (cost=0.00..0.00 rows=1 width=64) (actual time=0.002..0.002 rows=0 loops=1)
        Filter: (invoice_no = '536365'::text)
Planning:
  Buffers: shared hit=487
Planning Time: 1.142 ms
Execution Time: 1.196 ms
```

## November partition query

Execution time: 24.559 ms

```text
HashAggregate  (cost=3921.86..3922.32 rows=37 width=40) (actual time=24.535..24.542 rows=24 loops=1)
  Group Key: fact_sales.country_key
  Batches: 1  Memory Usage: 32kB
  Buffers: shared hit=2255
  ->  Seq Scan on fact_sales_2011_11 fact_sales  (cost=0.00..3505.14 rows=83343 width=14) (actual time=0.004..12.598 rows=83343 loops=1)
        Filter: ((invoice_date >= '2011-11-01'::date) AND (invoice_date < '2011-12-01'::date))
        Buffers: shared hit=2255
Planning:
  Buffers: shared hit=73 read=1
Planning Time: 0.196 ms
Execution Time: 24.559 ms
```

## Base fact aggregation

Execution time: 134.131 ms

```text
Sort  (cost=27542.91..27571.12 rows=11285 width=44) (actual time=130.722..134.051 rows=314 loops=1)
  Sort Key: ((date_trunc('month'::text, (fact_sales.invoice_date)::timestamp with time zone))::date), fact_sales.country_key
  Sort Method: quicksort  Memory: 40kB
  Buffers: shared hit=14530
  ->  Finalize HashAggregate  (cost=26557.61..26783.31 rows=11285 width=44) (actual time=130.545..133.966 rows=314 loops=1)
        Group Key: ((date_trunc('month'::text, (fact_sales.invoice_date)::timestamp with time zone))::date), fact_sales.country_key
        Batches: 1  Memory Usage: 529kB
        Buffers: shared hit=14530
        ->  Gather  (cost=23849.21..26331.91 rows=22570 width=44) (actual time=130.235..133.661 rows=346 loops=1)
              Workers Planned: 2
              Workers Launched: 2
              Buffers: shared hit=14530
              ->  Partial HashAggregate  (cost=22849.21..23074.91 rows=11285 width=44) (actual time=126.188..126.294 rows=115 loops=3)
                    Group Key: ((date_trunc('month'::text, (fact_sales.invoice_date)::timestamp with time zone))::date), fact_sales.country_key
                    Batches: 1  Memory Usage: 465kB
                    Buffers: shared hit=14530
                    Worker 0:  Batches: 1  Memory Usage: 465kB
                    Worker 1:  Batches: 1  Memory Usage: 433kB
                    ->  Parallel Append  (cost=0.00..21172.22 rows=223598 width=18) (actual time=0.021..87.192 rows=178880 loops=3)
                          Buffers: shared hit=14530
                          ->  Parallel Seq Scan on fact_sales_2011_11 fact_sales_12  (cost=0.00..3112.94 rows=49025 width=18) (actual time=0.012..30.548 rows=83343 loops=1)
                                Buffers: shared hit=2255
                          ->  Parallel Seq Scan on fact_sales_2011_10 fact_sales_11  (cost=0.00..2241.33 rows=35276 width=18) (actual time=0.010..21.715 rows=59969 loops=1)
                                Buffers: shared hit=1624
                          ->  Parallel Seq Scan on fact_sales_2011_09 fact_sales_10  (cost=0.00..1863.27 rows=29330 width=18) (actual time=0.008..17.043 rows=49861 loops=1)
                                Buffers: shared hit=1350
                          ->  Parallel Seq Scan on fact_sales_2010_12 fact_sales_1  (cost=0.00..1569.16 rows=24695 width=18) (actual time=0.006..14.814 rows=41981 loops=1)
                                Buffers: shared hit=1137
                          ->  Parallel Seq Scan on fact_sales_2011_07 fact_sales_8  (cost=0.00..1467.22 rows=23098 width=18) (actual time=0.008..12.898 rows=39267 loops=1)
                                Buffers: shared hit=1063
                          ->  Parallel Seq Scan on fact_sales_2011_05 fact_sales_6  (cost=0.00..1374.63 rows=21636 width=18) (actual time=0.005..25.852 rows=36782 loops=1)
                                Buffers: shared hit=996
                          ->  Parallel Seq Scan on fact_sales_2011_06 fact_sales_7  (cost=0.00..1367.86 rows=21535 width=18) (actual time=0.012..13.788 rows=36609 loops=1)
                                Buffers: shared hit=991
                          ->  Parallel Seq Scan on fact_sales_2011_03 fact_sales_4  (cost=0.00..1362.11 rows=21435 width=18) (actual time=0.004..5.238 rows=12146 loops=3)
                                Buffers: shared hit=987
                          ->  Parallel Seq Scan on fact_sales_2011_08 fact_sales_9  (cost=0.00..1309.93 rows=20625 width=18) (actual time=0.007..11.999 rows=17531 loops=2)
                                Buffers: shared hit=949
                          ->  Parallel Seq Scan on fact_sales_2011_01 fact_sales_2  (cost=0.00..1304.26 rows=20529 width=18) (actual time=0.003..13.344 rows=34900 loops=1)
                                Buffers: shared hit=945
                          ->  Parallel Seq Scan on fact_sales_2011_04 fact_sales_5  (cost=0.00..1110.74 rows=17471 width=18) (actual time=0.003..9.499 rows=29701 loops=1)
                                Buffers: shared hit=805
                          ->  Parallel Seq Scan on fact_sales_2011_02 fact_sales_3  (cost=0.00..1026.87 rows=16164 width=18) (actual time=0.005..13.674 rows=27479 loops=1)
                                Buffers: shared hit=744
                          ->  Parallel Seq Scan on fact_sales_2011_12 fact_sales_13  (cost=0.00..943.89 rows=14851 width=18) (actual time=0.007..14.035 rows=25246 loops=1)
                                Buffers: shared hit=684
                          ->  Parallel Seq Scan on fact_sales_default fact_sales_14  (cost=0.00..0.01 rows=1 width=18) (actual time=0.001..0.001 rows=0 loops=1)
Planning:
  Buffers: shared hit=143
Planning Time: 0.409 ms
Execution Time: 134.131 ms
```

## Materialized cache query

Execution time: 0.088 ms

```text
Sort  (cost=20.16..20.95 rows=314 width=19) (actual time=0.064..0.073 rows=314 loops=1)
  Sort Key: sales_month, country_key
  Sort Method: quicksort  Memory: 40kB
  Buffers: shared hit=4
  ->  Seq Scan on monthly_sales_summary  (cost=0.00..7.14 rows=314 width=19) (actual time=0.005..0.031 rows=314 loops=1)
        Buffers: shared hit=4
Planning:
  Buffers: shared hit=31
Planning Time: 0.091 ms
Execution Time: 0.088 ms
```
