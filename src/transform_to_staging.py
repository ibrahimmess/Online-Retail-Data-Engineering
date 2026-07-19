from dataclasses import dataclass
import hashlib
import json
import os

import pandas as pd

from src.config import PROJECT_ROOT
from src.database import (
    copy_dataframe,
    get_connection,
)


SOURCE_COLUMNS = [
    "invoice_no",
    "stock_code",
    "description",
    "quantity",
    "invoice_date",
    "unit_price",
    "customer_id",
    "country",
]


COUNTRY_MAPPING = {
    "EIRE": "Ireland",
    "RSA": "South Africa",
}


@dataclass
class TransformResult:
    clean: pd.DataFrame
    exclusions: pd.DataFrame
    metrics: dict
    thresholds: dict


def normalize_text(
    series: pd.Series,
    *,
    uppercase: bool = False,
) -> pd.Series:
    normalized = (
        series.astype("string")
        .str.strip()
        .str.replace(
            r"\s+",
            " ",
            regex=True,
        )
    )

    normalized = normalized.mask(
        normalized.eq(""),
        pd.NA,
    )

    if uppercase:
        normalized = normalized.str.upper()

    return normalized


def add_reason(
    reasons: pd.Series,
    condition: pd.Series,
    reason: str,
) -> None:
    condition = condition.fillna(False)

    reasons.loc[condition] = reasons.loc[
        condition
    ].apply(
        lambda current: (
            f"{current};{reason}"
            if current
            else reason
        )
    )


def calculate_row_hashes(
    raw_rows: pd.DataFrame,
) -> list[str]:
    hashes = []

    for values in raw_rows[
        SOURCE_COLUMNS
    ].itertuples(
        index=False,
        name=None,
    ):
        canonical_value = "\x1f".join(
            "" if value is None else str(value)
            for value in values
        )

        hashes.append(
            hashlib.sha256(
                canonical_value.encode("utf-8")
            ).hexdigest()
        )

    return hashes


def classify_products(
    stock_code: pd.Series,
    description: pd.Series,
) -> pd.Series:
    result = pd.Series(
        "OTHER",
        index=stock_code.index,
        dtype="string",
    )

    product_mask = stock_code.str.match(
        r"^[0-9]{5}[A-Z]?$",
        na=False,
    )

    result.loc[product_mask] = "PRODUCT"

    result.loc[
        stock_code.isin(
            ["POST", "DOT", "C2"]
        )
    ] = "SHIPPING"

    result.loc[
        stock_code.isin(
            [
                "AMAZONFEE",
                "BANK CHARGES",
                "CRUK",
                "M",
            ]
        )
    ] = "FEE"

    result.loc[
        stock_code.isin(["D", "DISC"])
        | description.str.contains(
            "DISCOUNT",
            case=False,
            na=False,
        )
    ] = "DISCOUNT"

    return result


def build_exclusions(
    raw: pd.DataFrame,
    indices: pd.Index,
    batch_id: str,
    exclusion_type: str,
    reasons: pd.Series,
) -> pd.DataFrame:
    columns = [
        "batch_id",
        "source_row_number",
        "exclusion_type",
        "reasons",
        "raw_record",
    ]

    if len(indices) == 0:
        return pd.DataFrame(columns=columns)

    source_records = raw.loc[
        indices,
        SOURCE_COLUMNS,
    ].to_dict(orient="records")

    return pd.DataFrame(
        {
            "batch_id": batch_id,
            "source_row_number": raw.loc[
                indices,
                "source_row_number",
            ].astype("int64"),
            "exclusion_type": exclusion_type,
            "reasons": reasons.loc[
                indices
            ].astype("string"),
            "raw_record": [
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                for record in source_records
            ],
        }
    ).reset_index(drop=True)


def transform_dataframe(
    raw: pd.DataFrame,
    batch_id: str,
) -> TransformResult:
    transformed = pd.DataFrame(
        index=raw.index
    )

    transformed["source_row_number"] = raw[
        "source_row_number"
    ].astype("int64")

    transformed["invoice_no"] = normalize_text(
        raw["invoice_no"]
    )

    transformed["stock_code"] = normalize_text(
        raw["stock_code"],
        uppercase=True,
    )

    transformed["description"] = normalize_text(
        raw["description"],
        uppercase=True,
    )

    transformed["quantity"] = pd.to_numeric(
        raw["quantity"],
        errors="coerce",
    ).astype("Int64")

    transformed["invoice_timestamp"] = (
        pd.to_datetime(
            raw["invoice_date"],
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )
    )

    transformed["unit_price"] = pd.to_numeric(
        raw["unit_price"],
        errors="coerce",
    )

    customer_id = normalize_text(
        raw["customer_id"]
    )

    transformed["customer_id"] = (
        customer_id.str.replace(
            r"^(\d+)\.0$",
            r"\1",
            regex=True,
        )
    )

    transformed["source_country"] = (
        normalize_text(raw["country"])
    )

    transformed["country"] = transformed[
        "source_country"
    ].replace(COUNTRY_MAPPING)

    reasons = pd.Series(
        "",
        index=raw.index,
        dtype="string",
    )

    add_reason(
        reasons,
        transformed["invoice_no"].isna(),
        "MISSING_INVOICE_NO",
    )

    add_reason(
        reasons,
        transformed["stock_code"].isna(),
        "MISSING_STOCK_CODE",
    )

    add_reason(
        reasons,
        transformed[
            "invoice_timestamp"
        ].isna(),
        "INVALID_INVOICE_DATE",
    )

    add_reason(
        reasons,
        transformed["quantity"].isna(),
        "INVALID_QUANTITY",
    )

    add_reason(
        reasons,
        transformed["quantity"].eq(0),
        "ZERO_QUANTITY",
    )

    add_reason(
        reasons,
        transformed["unit_price"].isna(),
        "INVALID_UNIT_PRICE",
    )

    add_reason(
        reasons,
        transformed["unit_price"].lt(0),
        "NEGATIVE_UNIT_PRICE",
    )

    add_reason(
        reasons,
        transformed["country"].isna(),
        "MISSING_COUNTRY",
    )

    rejected_indices = reasons.loc[
        reasons.ne("")
    ].index

    valid_indices = reasons.loc[
        reasons.eq("")
    ].index

    duplicate_mask = raw.loc[
        valid_indices,
        SOURCE_COLUMNS,
    ].duplicated(keep="first")

    duplicate_indices = duplicate_mask.loc[
        duplicate_mask
    ].index

    accepted_indices = valid_indices.difference(
        duplicate_indices,
        sort=False,
    )

    accepted = transformed.loc[
        accepted_indices
    ].copy()

    if accepted.empty:
        description_mapping = pd.Series(
            dtype="string"
        )
    else:
        description_counts = (
            accepted.dropna(
                subset=["description"]
            )
            .groupby(
                [
                    "stock_code",
                    "description",
                ],
                as_index=False,
            )
            .size()
            .sort_values(
                [
                    "stock_code",
                    "size",
                    "description",
                ],
                ascending=[
                    True,
                    False,
                    True,
                ],
            )
            .drop_duplicates("stock_code")
        )

        description_mapping = (
            description_counts.set_index(
                "stock_code"
            )["description"]
        )

    accepted[
        "description_was_missing"
    ] = accepted["description"].isna()

    accepted["description"] = accepted[
        "description"
    ].fillna(
        accepted["stock_code"].map(
            description_mapping
        )
    )

    accepted[
        "description_is_unknown"
    ] = accepted["description"].isna()

    accepted["description"] = accepted[
        "description"
    ].fillna("UNKNOWN PRODUCT")

    accepted["product_type"] = (
        classify_products(
            accepted["stock_code"],
            accepted["description"],
        )
    )

    accepted["invoice_date"] = accepted[
        "invoice_timestamp"
    ].dt.date

    accepted["is_cancellation"] = accepted[
        "invoice_no"
    ].str.startswith("C")

    accepted["transaction_type"] = "SALE"

    accepted.loc[
        accepted["unit_price"].eq(0),
        "transaction_type",
    ] = "ZERO_PRICE"

    accepted.loc[
        accepted["quantity"].lt(0),
        "transaction_type",
    ] = "RETURN_OR_ADJUSTMENT"

    accepted.loc[
        accepted["is_cancellation"],
        "transaction_type",
    ] = "CANCELLATION"

    accepted["is_zero_price"] = accepted[
        "unit_price"
    ].eq(0)

    if accepted.empty:
        quantity_threshold = 0.0
        price_threshold = 0.0
    else:
        quantity_threshold = float(
            accepted["quantity"]
            .abs()
            .quantile(0.999)
        )

        price_threshold = float(
            accepted["unit_price"].quantile(
                0.999
            )
        )

    accepted[
        "is_quantity_outlier"
    ] = accepted["quantity"].abs().gt(
        quantity_threshold
    )

    accepted[
        "is_price_outlier"
    ] = accepted["unit_price"].gt(
        price_threshold
    )

    accepted["source_row_hash"] = (
        calculate_row_hashes(
            raw.loc[accepted_indices]
        )
    )

    accepted.insert(
        0,
        "batch_id",
        batch_id,
    )

    clean_columns = [
        "batch_id",
        "source_row_number",
        "invoice_no",
        "stock_code",
        "description",
        "product_type",
        "quantity",
        "invoice_timestamp",
        "invoice_date",
        "unit_price",
        "customer_id",
        "source_country",
        "country",
        "transaction_type",
        "is_cancellation",
        "is_zero_price",
        "is_quantity_outlier",
        "is_price_outlier",
        "description_was_missing",
        "description_is_unknown",
        "source_row_hash",
    ]

    clean = accepted[
        clean_columns
    ].reset_index(drop=True)

    rejected = build_exclusions(
        raw,
        rejected_indices,
        batch_id,
        "REJECTED",
        reasons,
    )

    duplicate_reasons = pd.Series(
        "EXACT_DUPLICATE",
        index=raw.index,
        dtype="string",
    )

    duplicates = build_exclusions(
        raw,
        duplicate_indices,
        batch_id,
        "DUPLICATE",
        duplicate_reasons,
    )

    exclusions = pd.concat(
        [rejected, duplicates],
        ignore_index=True,
    )

    metrics = {
        "raw_rows": len(raw),
        "accepted_rows": len(clean),
        "rejected_rows": len(
            rejected_indices
        ),
        "duplicate_rows": len(
            duplicate_indices
        ),
        "missing_customer_rows": int(
            clean["customer_id"]
            .isna()
            .sum()
        ),
        "missing_description_before_recovery": int(
            clean[
                "description_was_missing"
            ].sum()
        ),
        "unknown_description_after_recovery": int(
            clean[
                "description_is_unknown"
            ].sum()
        ),
        "cancellation_rows": int(
            clean["is_cancellation"].sum()
        ),
        "negative_quantity_rows": int(
            clean["quantity"].lt(0).sum()
        ),
        "zero_price_rows": int(
            clean["is_zero_price"].sum()
        ),
        "quantity_outlier_rows": int(
            clean[
                "is_quantity_outlier"
            ].sum()
        ),
        "price_outlier_rows": int(
            clean["is_price_outlier"].sum()
        ),
        "unique_standardized_products": int(
            clean["stock_code"].nunique()
        ),
        "net_line_amount": round(
            float(
                (
                    clean["quantity"]
                    * clean["unit_price"]
                ).sum()
            ),
            2,
        ),
    }

    thresholds = {
        "absolute_quantity_p99_9": (
            quantity_threshold
        ),
        "unit_price_p99_9": price_threshold,
    }

    return TransformResult(
        clean=clean,
        exclusions=exclusions,
        metrics=metrics,
        thresholds=thresholds,
    )


def find_latest_batch() -> tuple[str, str]:
    requested_batch_id = os.getenv("ETL_BATCH_ID")

    with get_connection() as connection:
        if requested_batch_id:
            source = connection.execute(
                """
                SELECT
                    batch_id::TEXT,
                    status
                FROM audit.source_files
                WHERE
                    batch_id = %s
                    AND status IN (
                        'RAW_LOADED',
                        'TRANSFORMED',
                        'WAREHOUSE_LOADED',
                        'SUCCESS'
                    )
                """,
                (requested_batch_id,),
            ).fetchone()
        else:
            source = connection.execute(
                """
                SELECT
                    batch_id::TEXT,
                    status
                FROM audit.source_files
                WHERE status IN (
                    'RAW_LOADED',
                    'TRANSFORMED',
                    'WAREHOUSE_LOADED',
                    'SUCCESS'
                )
                ORDER BY registered_at DESC
                LIMIT 1
                """
            ).fetchone()

    if not source:
        if requested_batch_id:
            raise RuntimeError(
                "Requested ETL batch was not found or is not "
                "ready for transformation: "
                f"{requested_batch_id}"
            )

        raise RuntimeError(
            "No raw source batch found. "
            "Run python -m src.ingest_raw first."
        )

    return source[0], source[1]


def fetch_raw_batch(
    batch_id: str,
) -> pd.DataFrame:
    query = """
        SELECT
            source_row_number,
            invoice_no,
            stock_code,
            description,
            quantity,
            invoice_date,
            unit_price,
            customer_id,
            country
        FROM raw.online_retail
        WHERE batch_id = %s
        ORDER BY source_row_number
    """

    with get_connection() as connection:
        rows = connection.execute(
            query,
            (batch_id,),
        ).fetchall()

    columns = [
        "source_row_number",
        *SOURCE_COLUMNS,
    ]

    return pd.DataFrame(
        rows,
        columns=columns,
    )


def main() -> None:
    batch_id, current_status = (
        find_latest_batch()
    )

    with get_connection() as connection:
        existing_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM staging.online_retail_clean
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

    if (
        current_status
        in {
            "TRANSFORMED",
            "WAREHOUSE_LOADED",
            "SUCCESS",
        }
        and existing_count > 0
    ):
        print(
            "This batch was already transformed."
        )
        print(
            f"Staging rows: {existing_count:,}"
        )
        return

    print(f"Batch ID: {batch_id}")
    print("Reading raw rows from PostgreSQL...")

    raw = fetch_raw_batch(batch_id)

    print(f"Raw rows: {len(raw):,}")
    print("Cleaning and transforming...")

    result = transform_dataframe(
        raw,
        batch_id,
    )

    with get_connection() as connection:
        connection.execute(
            """
            DELETE FROM staging.online_retail_clean
            WHERE batch_id = %s
            """,
            (batch_id,),
        )

        connection.execute(
            """
            DELETE FROM audit.excluded_records
            WHERE batch_id = %s
            """,
            (batch_id,),
        )

        copy_dataframe(
            connection,
            result.exclusions,
            "audit.excluded_records",
            result.exclusions.columns,
        )

        copy_dataframe(
            connection,
            result.clean,
            "staging.online_retail_clean",
            result.clean.columns,
        )

        connection.execute(
            """
            UPDATE audit.source_files
            SET
                status = 'TRANSFORMED',
                updated_at = CURRENT_TIMESTAMP
            WHERE batch_id = %s
            """,
            (batch_id,),
        )

    report = {
        "batch_id": batch_id,
        "metrics": result.metrics,
        "outlier_thresholds": (
            result.thresholds
        ),
    }

    report_file = (
        PROJECT_ROOT
        / "reports"
        / "cleaning_report.json"
    )

    report_file.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print("------------------------------")
    print("TRANSFORMATION COMPLETED")
    print("------------------------------")

    for name, value in result.metrics.items():
        if isinstance(value, int):
            value = f"{value:,}"

        print(f"{name}: {value}")

    print(
        "quantity_outlier_threshold: "
        f"{result.thresholds['absolute_quantity_p99_9']}"
    )

    print(
        "price_outlier_threshold: "
        f"{result.thresholds['unit_price_p99_9']:.6f}"
    )

    print("------------------------------")
    print(f"Report: {report_file}")


if __name__ == "__main__":
    main()