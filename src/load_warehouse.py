import os

from src.database import get_connection


def find_latest_batch() -> tuple[str, str]:
    requested_batch_id = os.getenv("ETL_BATCH_ID")

    with get_connection() as connection:
        if requested_batch_id:
            result = connection.execute(
                """
                SELECT
                    batch_id::TEXT,
                    status
                FROM audit.source_files
                WHERE
                    batch_id = %s
                    AND status IN (
                        'TRANSFORMED',
                        'WAREHOUSE_LOADED',
                        'SUCCESS'
                    )
                """,
                (requested_batch_id,),
            ).fetchone()
        else:
            result = connection.execute(
                """
                SELECT
                    batch_id::TEXT,
                    status
                FROM audit.source_files
                WHERE status IN (
                    'TRANSFORMED',
                    'WAREHOUSE_LOADED',
                    'SUCCESS'
                )
                ORDER BY registered_at DESC
                LIMIT 1
                """
            ).fetchone()

    if not result:
        if requested_batch_id:
            raise RuntimeError(
                "Requested ETL batch was not found or is not "
                "ready for warehouse loading: "
                f"{requested_batch_id}"
            )

        raise RuntimeError(
            "No transformed batch found."
        )

    return result[0], result[1]


def record_inserted_rows(inserted_rows: int) -> None:
    run_id = os.getenv("ETL_RUN_ID")

    if not run_id:
        return

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE audit.etl_runs
            SET fact_rows_inserted = %s
            WHERE run_id = %s
            """,
            (inserted_rows, run_id),
        )


def main() -> None:
    batch_id, current_status = (
        find_latest_batch()
    )

    print(f"Batch ID: {batch_id}")

    with get_connection() as connection:
        staging_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM staging.online_retail_clean
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

        fact_presence_count = connection.execute(
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

        membership_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM audit.batch_fact_membership
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

    if (
        current_status
        in {"WAREHOUSE_LOADED", "SUCCESS"}
        and fact_presence_count
        == staging_count
        and membership_count
        == staging_count
    ):
        print(
            "This batch is already present "
            "in the warehouse."
        )
        print(
            f"Fact candidates present: "
            f"{fact_presence_count:,}"
        )
        print(
            f"Batch memberships present: "
            f"{membership_count:,}"
        )
        record_inserted_rows(0)
        return

    print("Loading dimensions and facts...")

    with get_connection() as connection:
        inserted_rows = connection.execute(
            """
            SELECT warehouse.load_batch(%s)
            """,
            (batch_id,),
        ).fetchone()[0]

        connection.execute(
            """
            UPDATE audit.source_files
            SET
                status = 'WAREHOUSE_LOADED',
                updated_at = CURRENT_TIMESTAMP
            WHERE batch_id = %s
            """,
            (batch_id,),
        )

    record_inserted_rows(inserted_rows)

    with get_connection() as connection:
        counts = {
            "dim_product": connection.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.dim_product
                """
            ).fetchone()[0],

            "dim_customer": connection.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.dim_customer
                """
            ).fetchone()[0],

            "dim_country": connection.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.dim_country
                """
            ).fetchone()[0],

            "dim_date": connection.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.dim_date
                """
            ).fetchone()[0],

            "fact_sales": connection.execute(
                """
                SELECT COUNT(*)
                FROM warehouse.fact_sales
                """
            ).fetchone()[0],

            "net_revenue": connection.execute(
                """
                SELECT ROUND(
                    SUM(line_amount),
                    2
                )
                FROM warehouse.fact_sales
                """
            ).fetchone()[0],
        }

    print("------------------------------")
    print("WAREHOUSE LOAD COMPLETED")
    print("------------------------------")
    print(
        f"Facts inserted now: "
        f"{inserted_rows:,}"
    )

    for table_name, count in counts.items():
        print(f"{table_name}: {count:,}")


if __name__ == "__main__":
    main()