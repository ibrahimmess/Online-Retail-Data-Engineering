# Archived dataset versions

The ETL creates immutable archived copies under:

```text
data/archive/YYYY-MM-DD/<sha256>/online_retail.csv
data/archive/YYYY-MM-DD/<sha256>/manifest.json
```

Archived CSV files are intentionally not ignored by Git. Include at least one generated archive in the final submission, or submit the source dataset as a separate file when repository size limits apply.
