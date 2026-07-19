# Data Dictionary

## Purpose

This document describes the source fields, analytical fields, warehouse keys, measures, quality flags, and lineage information used by the Online Retail ETL pipeline.

## Source dataset

| Source column | Meaning | Raw representation | Analytical representation | Nullable |
|---|---|---|---|---|
| `InvoiceNo` | Transaction invoice identifier | Text | Standardized text | Yes in raw |
| `StockCode` | Product identifier | Text | Standardized text | Yes in raw |
| `Description` | Product description | Text | Trimmed and standardized text | Yes |
| `Quantity` | Number of items purchased or returned | Text | Integer | Yes in raw |
| `InvoiceDate` | Date and time of the transaction | Text | Timestamp | Yes in raw |
| `UnitPrice` | Price of one product unit | Text | Numeric/decimal | Yes in raw |
| `CustomerID` | Customer identifier | Text | Normalized customer identifier | Yes |
| `Country` | Customer or transaction country | Text | Standardized text | Yes in raw |

All source columns are initially stored as text so the raw layer preserves the original CSV representation before validation or conversion.

## Audit layer

### `audit.source_files`

Stores one record for each unique source-file version.

| Column | Meaning |
|---|---|
| `batch_id` | Unique identifier assigned to the ingestion batch |
| `source_file_name` | Original filename |
| `source_file_path` | Location from which the file was ingested |
| `sha256` | Unique SHA-256 checksum for source versioning |
| `file_size_bytes` | Source-file size in bytes |
| `row_count` | Number of source data rows |
| `status` | Source processing state such as `REGISTERED`, `RAW_LOADED`, or `FAILED` |
| `registered_at` | Time the source was registered |
| `updated_at` | Time the audit record was last updated |

### ETL execution records

The audit layer also records pipeline executions, processing status, timestamps, metrics, errors, and data-quality results. These records make each run observable and reproducible.

### Quality results

| Field | Meaning |
|---|---|
| Check name | Unique name of the quality rule |
| Status | `PASS`, `WARN`, or `FAIL` |
| Observed value | Value calculated during validation |
| Expected value | Required value or threshold |
| Details | Additional structured information about the result |
| Checked at | Time the check was executed |

## Raw layer

### `raw.online_retail`

Contains the immutable source representation.

| Column | Meaning |
|---|---|
| `batch_id` | Foreign key to the registered source version |
| `source_row_number` | Original CSV row number, including the header offset |
| `invoice_no` | Original invoice value |
| `stock_code` | Original product-code value |
| `description` | Original description value |
| `quantity` | Original quantity stored as text |
| `invoice_date` | Original date stored as text |
| `unit_price` | Original price stored as text |
| `customer_id` | Original customer value stored as text |
| `country` | Original country value |
| `ingested_at` | Time the row entered PostgreSQL |

The combination of `batch_id` and `source_row_number` uniquely identifies a raw record.

## Staging layer

### `staging.online_retail_clean`

Contains accepted, standardized, and correctly typed records.

| Field | Meaning |
|---|---|
| `batch_id` | Source batch lineage |
| `source_row_number` | Original CSV row lineage |
| `invoice_no` | Clean invoice identifier |
| `stock_code` | Clean product identifier |
| `description` | Trimmed and standardized product description |
| `quantity` | Signed integer quantity |
| `invoice_date` | Parsed transaction timestamp |
| `unit_price` | Decimal unit price |
| `customer_id` | Normalized customer identifier; nullable for anonymous transactions |
| `country` | Standardized country |
| `line_amount` | Quantity multiplied by unit price |
| Cancellation/return flag | Identifies cancellations or negative-quantity activity |
| Missing-customer flag | Identifies anonymous transactions |
| Quality fields | Explain validation or transformation outcomes |

Exact duplicates and negative-price records are excluded from this accepted analytical dataset. Their handling is captured through audit metrics or rejection records.

## Warehouse dimensions

### Product dimension

Represents products independently from individual transactions.

| Field | Meaning |
|---|---|
| Product key | Warehouse surrogate key |
| `stock_code` | Source business key |
| `description` | Standardized product description |
| Batch/lineage fields | Source version or processing lineage |
| Audit timestamps | Creation or update timestamps |

### Customer dimension

Represents known and anonymous customers.

| Field | Meaning |
|---|---|
| Customer key | Warehouse surrogate key |
| `customer_id` | Normalized source customer identifier |
| Anonymous/unknown indicator | Distinguishes missing customer IDs |
| Batch/lineage fields | Source version or processing lineage |
| Audit timestamps | Creation or update timestamps |

### Country dimension

Standardizes countries used for geographical analysis.

| Field | Meaning |
|---|---|
| Country key | Warehouse surrogate key |
| `country` | Standardized country name |
| Audit fields | Record creation or update information |

### Date dimension

Supports efficient date-based grouping and filtering.

| Field | Meaning |
|---|---|
| Date key | Warehouse date identifier |
| Full date | Calendar date |
| Day | Day of month |
| Month | Calendar month number |
| Month name | Calendar month label |
| Quarter | Calendar quarter |
| Year | Calendar year |
| Day of week | Weekday number or name |
| Weekend indicator | Whether the date falls on a weekend |

## Sales fact table

### `warehouse.fact_sales`

Stores transaction-line measures and references to dimensions.

| Field | Category | Meaning |
|---|---|---|
| Sales key | Primary key | Unique warehouse fact identifier |
| Product key | Foreign key | Reference to the product dimension |
| Customer key | Foreign key | Reference to the customer dimension |
| Country key | Foreign key | Reference to the country dimension |
| Date key | Foreign key | Reference to the date dimension |
| `invoice_no` | Degenerate dimension | Source invoice identifier |
| `invoice_date` | Transaction attribute | Exact transaction timestamp |
| `quantity` | Measure | Signed number of units |
| `unit_price` | Measure | Price per unit |
| `line_amount` | Measure | Quantity multiplied by unit price |
| Cancellation/return flag | Quality/status flag | Identifies cancellation or return activity |
| Missing-customer flag | Quality flag | Identifies anonymous transactions |
| `batch_id` | Lineage | Source-file version |
| `source_row_number` | Lineage | Original CSV row |
| Load timestamp | Audit field | Time the row entered the warehouse |

The signed quantity and line amount preserve returns and cancellations, enabling net-sales calculations.

## Quality rules and flags

| Rule or flag | Interpretation |
|---|---|
| Exact duplicate | Entire source record repeats a previous record |
| Invalid unit price | Unit price is negative or cannot be parsed |
| Invalid quantity | Quantity cannot be converted to an integer |
| Invalid invoice date | Invoice timestamp cannot be parsed |
| Missing customer | Customer identifier is absent; transaction remains valid |
| Missing description | Product description is absent or requires recovery |
| Cancellation | Invoice number begins with `C` |
| Return | Quantity is negative |
| Zero price | Unit price equals zero and is retained for monitoring |
| Accepted record | Record passed all rejection rules |
| Rejected record | Record failed a mandatory analytical rule |

## Derived measures

| Measure | Formula |
|---|---|
| Line amount | `quantity × unit_price` |
| Net revenue | Sum of signed `line_amount` |
| Units | Sum of signed `quantity` |
| Transaction count | Count of fact rows or distinct invoices, depending on the report |
| Customer count | Count of distinct known customer identifiers |

## Lineage

Every analytical record can be traced through:

```text
warehouse fact
    → batch_id and source_row_number
    → staging record
    → raw record
    → audit.source_files
    → original source checksum and archived version
```

This lineage makes the transformations auditable and supports reproduction of historical runs.

## Storage locations

| Asset | Location |
|---|---|
| Active source CSV | `data/raw/online_retail.csv` |
| Archived source versions | `data/archive/` |
| Source profile | `reports/source_profile.json` |
| Cleaning and quality reports | `reports/` |
| Query-performance report | `reports/` |
| ETL logs | `logs/` |
| SQL definitions | `sql/` |
| Pipeline code | `src/` |
| Automated tests | `tests/` |