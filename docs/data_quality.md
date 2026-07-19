# Data Quality Monitoring

## Cleaning results

| Metric | Value |
|---|---:|
| Raw rows | 541,909 |
| Accepted rows | 536,639 |
| Exact duplicates | 5,268 |
| Rejected negative-price rows | 2 |
| Missing CustomerID in raw | 135,080 |
| Missing descriptions in raw | 1,454 |

## Decisions

- Missing customers are retained and mapped to UNKNOWN.
- Missing descriptions are recovered using standardized StockCode where possible.
- Exact duplicates remain in raw but are excluded from facts.
- C-prefixed invoices are cancellations and are retained.
- Other negative quantities are classified as returns or adjustments.
- Zero-price records are retained and flagged.
- Negative-price records are quarantined.
- Outliers are flagged instead of deleted.

## Critical checks

- Raw database count equals source count.
- Raw equals accepted plus rejected plus duplicates.
- Every accepted row exists in the fact table.
- Cancellations have negative quantities.
- Fact foreign keys are populated.

## Warning thresholds

- Missing customer rate: maximum 30%.
- Unknown description rate: maximum 0.1%.
- Duplicate rate: maximum 2%.
- Rejected-record rate: maximum 1%.
- Zero-price rate: maximum 1%.

Warnings and failures are written to `logs/alerts.log`. An optional webhook can also be configured.