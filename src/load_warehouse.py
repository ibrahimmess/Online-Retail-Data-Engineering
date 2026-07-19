from src.database import get_connection


def find_latest_batch() -> tuple[str, str]:
    with get_connection() as connection:
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
        raise RuntimeError(
            "No transformed batch found."
        )

    return result[0], result[1]


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

    if (
        current_status
        in {"WAREHOUSE_LOADED", "SUCCESS"}
        and fact_presence_count
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