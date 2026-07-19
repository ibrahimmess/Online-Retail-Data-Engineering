# Online Retail Data Engineering Pipeline

## Project objective

This project implements a reproducible ETL pipeline for an online retail dataset. It ingests a CSV source into PostgreSQL, validates and cleans the data, transforms it into an analytical star schema, monitors data quality, tracks dataset versions and lineage, and optimizes reporting queries.

## Dataset profile

The source dataset contains online retail transactions recorded between December 2010 and December 2011.

| Metric | Value |
|---|---:|
| Raw rows | 541,909 |
| Columns | 8 |
| Unique invoices | 25,900 |
| Unique products | 4,070 |
| Known customers | 4,372 |
| Countries | 38 |
| Missing CustomerID | 135,080 |
| Missing Description | 1,454 |
| Exact duplicate rows | 5,268 |
| Negative quantity rows | 10,624 |
| Cancellation rows | 9,288 |
| Zero unit-price rows | 2,515 |
| Negative unit-price rows | 2 |
| Accepted analytical rows | 536,639 |
| Rejected rows | 2 |
| Net line amount | 9,748,131.07 |

The source file is identified using this SHA-256 checksum:

```text
c820e928a9cb01d05738b0c36b5033ef661eccfb82f09f2e5ce8542da73b0b99
```

## Architecture

The pipeline uses four PostgreSQL schemas:

- `raw`: immutable representation of the original CSV.
- `staging`: cleaned, standardized, and typed records.
- `warehouse`: dimensional model for analytics.
- `audit`: source versions, ETL runs, quality results, rejected records, metadata, and lineage.

The main data flow is:

```text
CSV source
    → checksum and archive
    → raw text layer
    → cleaning and validation
    → typed staging layer
    → dimensions and sales fact
    → materialized reporting cache
```

The warehouse follows a star schema centred on `warehouse.fact_sales`, supported by product, customer, country, and date dimensions.

See [docs/architecture.md](docs/architecture.md) for more details.

## Project structure

```text
Online-Retail-Data-Engineering/
├── data/
│   ├── archive/
│   └── raw/
├── docs/
│   ├── architecture.md
│   ├── data_dictionary.md
│   ├── data_quality.md
│   ├── performance.md
│   └── recommendations.md
├── logs/
├── reports/
├── scripts/
├── sql/
├── src/
├── tests/
├── .env.example
├── .gitignore
├── compose.yaml
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.11 or newer
- Docker Desktop
- Docker Compose
- Visual Studio Code or another code editor
- PowerShell on Windows

## Installation

Clone or extract the project and open its root folder in VS Code.

Create the local environment configuration:

```powershell
Copy-Item .env.example .env
```

Create and activate a Python virtual environment:

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Install the Python dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Place the dataset at:

```text
data/raw/online_retail.csv
```

Start PostgreSQL:

```powershell
docker compose up -d
docker compose ps
```

Expected database status:

```text
online-retail-postgres    Up ... (healthy)
```

## Dataset profiling

Run:

```powershell
python src/profile_data.py
```

Expected principal results:

```text
Rows:                    541,909
Columns:                 8
Exact duplicates:        5,268
Negative unit prices:    2
```

The complete source profile is written to:

```text
reports/source_profile.json
```

## Database setup

Apply all SQL schema files in filename order:

```powershell
python -m src.setup_database
```

Expected ending:

```text
Database setup completed successfully.
```

## Raw ingestion

Load the source into the immutable raw layer:

```powershell
python -m src.ingest_raw
```

Expected result on the first execution:

```text
Rows loaded:    541,909
Database rows:  541,909
Status:         RAW_LOADED
```

Running the same ingestion again does not duplicate the source rows because the source checksum is already registered.

## Complete ETL pipeline

Run:

```powershell
python -m src.run_etl
```

Expected ending:

```text
PIPELINE COMPLETED SUCCESSFULLY
```

Expected warehouse results:

| Result | Expected value |
|---|---:|
| Raw rows | 541,909 |
| Staging rows | 536,639 |
| Fact rows | 536,639 |
| Rejected rows | 2 |
| Exact duplicates excluded | 5,268 |
| Net revenue | 9,748,131.07 |
| Cached reporting rows | 314 |

The orchestrator creates an `audit.etl_runs` record before the first ETL stage. It updates `current_stage` during execution, records the actual number of fact rows inserted during that run, stores the number of accepted rows reconciled to facts, and records failures with an error message.

Inspect the latest run with:

```powershell
docker compose exec postgres psql -U retail -d retail_dw -c "SELECT run_id, batch_id, status, current_stage, fact_rows_inserted, fact_rows_reconciled, warning_count, error_message, started_at, finished_at FROM audit.etl_runs ORDER BY started_at DESC LIMIT 5;"
```

## Cleaning and transformation rules

The pipeline:

- preserves the original source values in the raw layer;
- converts invoice dates, quantities, prices, and customer identifiers to appropriate data types;
- trims and standardizes text fields;
- excludes exact duplicate rows from the analytical layer;
- rejects the two rows containing negative unit prices;
- keeps cancellation and return transactions for correct net-sales analysis;
- permits missing customer identifiers for anonymous transactions;
- records source batch and row lineage;
- derives line amounts from quantity multiplied by unit price;
- adds quality and transaction-status flags.

Missing customer IDs are retained as unknown or anonymous customers rather than causing valid transactions to be discarded.

## Data-quality monitoring

Quality checks are stored in PostgreSQL and evaluated during pipeline execution. They cover:

- source and warehouse row counts;
- duplicate handling;
- negative prices;
- invalid dates;
- missing mandatory identifiers;
- referential integrity;
- warehouse reconciliation;
- revenue reconciliation;
- source-version consistency.

Expected quality summary:

```text
11 PASS, 0 WARN, 0 FAIL
```

An optional webhook can be configured in `.env`:

```env
ALERT_WEBHOOK_URL=
```

When the variable is empty, quality results are still recorded locally without sending an external alert.

See [docs/data_quality.md](docs/data_quality.md).

## Dataset versioning and lineage

Each source file is identified by its SHA-256 checksum. The audit layer stores:

- batch identifier;
- source filename and path;
- checksum;
- source size;
- source row count;
- ingestion status;
- registration and update timestamps.

Previous source versions are archived with a manifest for reproducibility and historical analysis. Archive paths are stored relative to the project root, for example:

```text
data/archive/2026-07-19/<sha256>/online_retail.csv
```

The warehouse stores one canonical fact for a repeated invoice line. `audit.batch_fact_membership` records every source version in which that fact appeared, so unchanged records remain traceable across snapshot deliveries. Include at least one generated archive in the final submission, or submit the source dataset separately when file-size limits apply.

## Metadata management

The metadata repository documents:

- schemas and tables;
- columns and data types;
- source-to-target mappings;
- transformation rules;
- storage locations;
- batch lineage;
- ETL execution history.

See [docs/data_dictionary.md](docs/data_dictionary.md).

## Tests

Run:

```powershell
python -m pytest
```

Expected result:

```text
6 passed
```

## Performance and caching

Run the query benchmarks:

```powershell
python -m src.benchmark_queries
```

The project uses:

- indexes on filtering and join columns;
- date-based partitioning for sales facts;
- PostgreSQL execution-plan analysis;
- a materialized view as a reporting cache.

Expected cached-row count:

```text
314
```

See [docs/performance.md](docs/performance.md).

## Scheduling

Register a daily Windows Task Scheduler job from the project root. Open PowerShell as Administrator and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\create_daily_task.ps1 -Time "06:00"
```

Verify that the task exists:

```powershell
Get-ScheduledTask -TaskName "Online Retail ETL"
```

Run it immediately for evidence:

```powershell
Start-ScheduledTask -TaskName "Online Retail ETL"
Start-Sleep -Seconds 10
Get-Content .\logs\task_scheduler.log -Tail 50
```

The task ignores a new trigger while a previous ETL run is still active. Failed scheduled executions retry up to three times at ten-minute intervals. Scheduled output is appended to:

```text
logs/task_scheduler.log
```

For the final submission, include a screenshot of the registered task or export its definition:

```powershell
Export-ScheduledTask -TaskName "Online Retail ETL" `
    | Out-File reports\online_retail_etl_task.xml -Encoding utf8
```

## Final verification

Run these commands in order:

```powershell
docker compose ps
python -m src.setup_database
python -m pytest
python -m src.run_etl
python -m src.benchmark_queries
```

Expected results:

```text
PostgreSQL: healthy
Tests: 6 passed
Pipeline: PIPELINE COMPLETED SUCCESSFULLY
Quality: 11 PASS, 0 WARN, 0 FAIL
Cached rows: 314
```

Verify the warehouse counts:

```powershell
docker compose exec postgres psql -U retail -d retail_dw -c "SELECT (SELECT COUNT(*) FROM raw.online_retail) AS raw_rows, (SELECT COUNT(*) FROM staging.online_retail_clean) AS staging_rows, (SELECT COUNT(*) FROM warehouse.fact_sales) AS fact_rows, (SELECT ROUND(SUM(line_amount),2) FROM warehouse.fact_sales) AS net_revenue;"
```

Expected result:

```text
raw_rows      = 541909
staging_rows  = 536639
fact_rows     = 536639
net_revenue   = 9748131.07
```

## Assumptions and limitations

- The project processes batch CSV files rather than streaming events.
- PostgreSQL and pandas are sufficient for the current dataset size.
- Missing customer identifiers represent anonymous transactions.
- Returns and cancellations are retained to support net-sales analysis.
- The local `.env` credentials are intended only for development.
- The materialized reporting cache must be refreshed after warehouse updates.
- A real webhook URL is required for external alert delivery.
- Production deployment would require managed secrets, backups, access controls, CI/CD, and operational monitoring.

## Recommendations

Future improvements include incremental loading, orchestration, cloud object storage, automated backups, schema migrations, OpenLineage-compatible metadata, and CI integration tests.

See [docs/recommendations.md](docs/recommendations.md).