from pathlib import Path
import hashlib
import json

import pandas as pd


DATA_FILE = Path("data/raw/online_retail.csv")
REPORT_FILE = Path("reports/source_profile.json")

EXPECTED_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


def calculate_sha256(file_path: Path) -> str:
    """Calculate a unique checksum for the source file."""
    file_hash = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            file_hash.update(chunk)

    return file_hash.hexdigest()


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found at {DATA_FILE}. "
            "Place online_retail.csv inside data/raw."
        )

    print("Reading the dataset...")

    dataframe = pd.read_csv(
        DATA_FILE,
        encoding="ISO-8859-1",
        dtype={
            "InvoiceNo": "string",
            "StockCode": "string",
            "Description": "string",
            "CustomerID": "string",
            "Country": "string",
        },
    )

    actual_columns = dataframe.columns.tolist()

    if actual_columns != EXPECTED_COLUMNS:
        raise ValueError(
            f"Unexpected columns.\n"
            f"Expected: {EXPECTED_COLUMNS}\n"
            f"Received: {actual_columns}"
        )

    invoice_dates = pd.to_datetime(
        dataframe["InvoiceDate"],
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
    )

    cancellation_mask = dataframe["InvoiceNo"].str.startswith("C", na=False)

    profile = {
        "file_name": DATA_FILE.name,
        "file_size_bytes": DATA_FILE.stat().st_size,
        "sha256": calculate_sha256(DATA_FILE),
        "row_count": int(len(dataframe)),
        "column_count": int(len(dataframe.columns)),
        "columns": actual_columns,
        "unique_invoices": int(dataframe["InvoiceNo"].nunique()),
        "unique_stock_codes": int(dataframe["StockCode"].nunique()),
        "unique_known_customers": int(dataframe["CustomerID"].nunique()),
        "unique_countries": int(dataframe["Country"].nunique()),
        "missing_customer_id": int(dataframe["CustomerID"].isna().sum()),
        "missing_description": int(dataframe["Description"].isna().sum()),
        "exact_duplicate_rows": int(dataframe.duplicated().sum()),
        "invalid_invoice_dates": int(invoice_dates.isna().sum()),
        "minimum_invoice_date": str(invoice_dates.min()),
        "maximum_invoice_date": str(invoice_dates.max()),
        "negative_quantity_rows": int(
            dataframe["Quantity"].lt(0).sum()
        ),
        "zero_quantity_rows": int(
            dataframe["Quantity"].eq(0).sum()
        ),
        "cancellation_rows": int(cancellation_mask.sum()),
        "negative_unit_price_rows": int(
            dataframe["UnitPrice"].lt(0).sum()
        ),
        "zero_unit_price_rows": int(
            dataframe["UnitPrice"].eq(0).sum()
        ),
        "minimum_quantity": int(dataframe["Quantity"].min()),
        "maximum_quantity": int(dataframe["Quantity"].max()),
        "minimum_unit_price": float(dataframe["UnitPrice"].min()),
        "maximum_unit_price": float(dataframe["UnitPrice"].max()),
    }

    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with REPORT_FILE.open("w", encoding="utf-8") as report:
        json.dump(profile, report, indent=2)

    print("\nDATASET PROFILE")
    print("------------------------------")
    print(f"Rows:                    {profile['row_count']:,}")
    print(f"Columns:                 {profile['column_count']}")
    print(f"Unique invoices:         {profile['unique_invoices']:,}")
    print(f"Unique stock codes:      {profile['unique_stock_codes']:,}")
    print(f"Unique known customers:  {profile['unique_known_customers']:,}")
    print(f"Countries:               {profile['unique_countries']:,}")
    print(f"Missing CustomerID:      {profile['missing_customer_id']:,}")
    print(f"Missing Description:     {profile['missing_description']:,}")
    print(f"Exact duplicates:        {profile['exact_duplicate_rows']:,}")
    print(f"Negative quantities:     {profile['negative_quantity_rows']:,}")
    print(f"Cancellation rows:       {profile['cancellation_rows']:,}")
    print(f"Zero unit prices:        {profile['zero_unit_price_rows']:,}")
    print(f"Negative unit prices:    {profile['negative_unit_price_rows']:,}")
    print(f"Minimum date:            {profile['minimum_invoice_date']}")
    print(f"Maximum date:            {profile['maximum_invoice_date']}")
    print(f"SHA-256:                 {profile['sha256']}")
    print("------------------------------")
    print(f"Profile saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()