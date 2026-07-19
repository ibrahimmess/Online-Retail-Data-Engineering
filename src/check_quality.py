from dataclasses import dataclass
import json
import uuid

from src.alerts import emit_alert
from src.database import get_connection


@dataclass
class QualityCheck:
    name: str
    dimension: str
    severity: str
    status: str
    observed: float
    expected_rule: str
    details: dict


def create_check(
    name: str,
    dimension: str,
    severity: str,
    observed: float,
    passed: bool,
    expected_rule: str,
    details: dict | None = None,
) -> QualityCheck:
    if passed:
        status = "PASS"
    elif severity == "CRITICAL":
        status = "FAIL"
    else:
        status = "WARN"

    return QualityCheck(
        name=name,
        dimension=dimension,
        severity=severity,
        status=status,
        observed=float(observed),
        expected_rule=expected_rule,
        details=details or {},
    )


def main() -> None:
    with get_connection() as connection:
        source = connection.execute(
            """
            SELECT batch_id::TEXT
            FROM audit.source_files
            WHERE status IN (
                'WAREHOUSE_LOADED',
                'SUCCESS'
            )
            ORDER BY registered_at DESC
            LIMIT 1
            """
        ).fetchone()

    if not source:
        raise RuntimeError(
            "No warehouse-loaded batch found."
        )

    batch_id = source[0]
    run_id = str(uuid.uuid4())

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit.etl_runs (
                run_id,
                batch_id,
                status
            )
            VALUES (
                %s,
                %s,
                'RUNNING'
            )
            """,
            (run_id, batch_id),
        )

    with get_connection() as connection:
        expected_raw_count = connection.execute(
            """
            SELECT row_count
            FROM audit.source_files
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

        raw_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM raw.online_retail
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

        staging_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM staging.online_retail_clean
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

        rejected_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit.excluded_records
            WHERE
                batch_id = %s
                AND exclusion_type = 'REJECTED'
            """,
            (batch_id,),
        ).fetchone()[0]

        duplicate_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit.excluded_records
            WHERE
                batch_id = %s
                AND exclusion_type = 'DUPLICATE'
            """,
            (batch_id,),
        ).fetchone()[0]

        facts_present = connection.execute(
            """
            SELECT COUNT(*)
            FROM staging.online_retail_clean
                AS source

            JOIN warehouse.fact_sales
                AS fact

                ON fact.invoice_date
                    = source.invoice_date

                AND fact.source_row_hash
                    = source.source_row_hash

            WHERE source.batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

        inconsistent_cancellations = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM staging.online_retail_clean
                WHERE
                    batch_id = %s
                    AND is_cancellation
                    AND quantity >= 0
                """,
                (batch_id,),
            ).fetchone()[0]
        )

        null_foreign_keys = connection.execute(
            """
            SELECT COUNT(*)
            FROM warehouse.fact_sales
            WHERE
                source_batch_id = %s
                AND (
                    date_key IS NULL
                    OR product_key IS NULL
                    OR customer_key IS NULL
                    OR country_key IS NULL
                )
            """,
            (batch_id,),
        ).fetchone()[0]

        missing_customers = connection.execute(
            """
            SELECT COUNT(*)
            FROM staging.online_retail_clean
            WHERE
                batch_id = %s
                AND customer_id IS NULL
            """,
            (batch_id,),
        ).fetchone()[0]

        unknown_descriptions = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM staging.online_retail_clean
                WHERE
                    batch_id = %s
                    AND description_is_unknown
                """,
                (batch_id,),
            ).fetchone()[0]
        )

        zero_prices = connection.execute(
            """
            SELECT COUNT(*)
            FROM staging.online_retail_clean
            WHERE
                batch_id = %s
                AND is_zero_price
            """,
            (batch_id,),
        ).fetchone()[0]

        default_partition_rows = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.fact_sales_default
                WHERE source_batch_id = %s
                """,
                (batch_id,),
            ).fetchone()[0]
        )

    safe_raw_count = max(raw_count, 1)
    safe_staging_count = max(
        staging_count,
        1,
    )

    missing_customer_rate = (
        missing_customers
        / safe_staging_count
    )

    unknown_description_rate = (
        unknown_descriptions
        / safe_staging_count
    )

    duplicate_rate = (
        duplicate_count
        / safe_raw_count
    )

    rejected_rate = (
        rejected_count
        / safe_raw_count
    )

    zero_price_rate = (
        zero_prices
        / safe_staging_count
    )

    checks = [
        create_check(
            "raw_database_count",
            "reconciliation",
            "CRITICAL",
            raw_count,
            raw_count == expected_raw_count,
            f"equals source row count "
            f"{expected_raw_count}",
        ),

        create_check(
            "row_reconciliation",
            "reconciliation",
            "CRITICAL",
            (
                staging_count
                + rejected_count
                + duplicate_count
            ),
            raw_count
            == (
                staging_count
                + rejected_count
                + duplicate_count
            ),
            "raw = accepted + rejected "
            "+ duplicates",
        ),

        create_check(
            "accepted_rows_exist_in_fact",
            "completeness",
            "CRITICAL",
            facts_present,
            facts_present
            == staging_count,
            f"equals staging count "
            f"{staging_count}",
        ),

        create_check(
            "cancellation_sign",
            "validity",
            "CRITICAL",
            inconsistent_cancellations,
            inconsistent_cancellations == 0,
            "C-prefixed invoices have "
            "negative quantities",
        ),

        create_check(
            "null_fact_foreign_keys",
            "referential_integrity",
            "CRITICAL",
            null_foreign_keys,
            null_foreign_keys == 0,
            "no null dimension keys",
        ),

        create_check(
            "missing_customer_rate",
            "completeness",
            "WARNING",
            missing_customer_rate,
            missing_customer_rate <= 0.30,
            "rate <= 30%",
        ),

        create_check(
            "unknown_description_rate",
            "completeness",
            "WARNING",
            unknown_description_rate,
            unknown_description_rate
            <= 0.001,
            "rate <= 0.1%",
        ),

        create_check(
            "duplicate_rate",
            "uniqueness",
            "WARNING",
            duplicate_rate,
            duplicate_rate <= 0.02,
            "rate <= 2%",
        ),

        create_check(
            "rejected_rate",
            "validity",
            "WARNING",
            rejected_rate,
            rejected_rate <= 0.01,
            "rate <= 1%",
        ),

        create_check(
            "zero_price_rate",
            "validity",
            "WARNING",
            zero_price_rate,
            zero_price_rate <= 0.01,
            "rate <= 1%",
        ),

        create_check(
            "default_partition_rows",
            "performance",
            "WARNING",
            default_partition_rows,
            default_partition_rows == 0,
            "0 rows for supplied date range",
        ),
    ]

    with get_connection() as connection:
        for check in checks:
            connection.execute(
                """
                INSERT INTO
                audit.data_quality_results (
                    run_id,
                    check_name,
                    quality_dimension,
                    severity,
                    status,
                    observed_value,
                    expected_rule,
                    details
                )
                VALUES (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s::JSONB
                )
                """,
                (
                    run_id,
                    check.name,
                    check.dimension,
                    check.severity,
                    check.status,
                    check.observed,
                    check.expected_rule,
                    json.dumps(check.details),
                ),
            )

        warning_count = sum(
            check.status == "WARN"
            for check in checks
        )

        failure_count = sum(
            check.status == "FAIL"
            for check in checks
        )

        final_status = (
            "FAILED"
            if failure_count
            else "SUCCESS"
        )

        connection.execute(
            """
            UPDATE audit.etl_runs
            SET
                status = %s,
                finished_at = CURRENT_TIMESTAMP,
                raw_rows = %s,
                accepted_rows = %s,
                rejected_rows = %s,
                duplicate_rows = %s,
                fact_rows_inserted = %s,
                warning_count = %s
            WHERE run_id = %s
            """,
            (
                final_status,
                raw_count,
                staging_count,
                rejected_count,
                duplicate_count,
                facts_present,
                warning_count,
                run_id,
            ),
        )

        connection.execute(
            """
            UPDATE audit.source_files
            SET
                status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE batch_id = %s
            """,
            (
                (
                    "FAILED"
                    if failure_count
                    else "SUCCESS"
                ),
                batch_id,
            ),
        )

    print("DATA-QUALITY RESULTS")
    print("------------------------------")

    for check in checks:
        print(
            f"[{check.status}] "
            f"{check.name}: "
            f"{check.observed:.6f}"
        )

    print("------------------------------")
    print(
        "PASS: "
        f"{sum(c.status == 'PASS' for c in checks)}"
    )
    print(
        "WARN: "
        f"{sum(c.status == 'WARN' for c in checks)}"
    )
    print(
        "FAIL: "
        f"{sum(c.status == 'FAIL' for c in checks)}"
    )

    problems = [
        check.name
        for check in checks
        if check.status in {"WARN", "FAIL"}
    ]

    if problems:
        emit_alert(
            "Data-quality issues: "
            + ", ".join(problems)
        )

    if any(
        check.status == "FAIL"
        for check in checks
    ):
        raise SystemExit(1)


if __name__ == "__main__":
    main()