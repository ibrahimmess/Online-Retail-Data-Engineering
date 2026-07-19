from src.database import get_connection


def main() -> None:
    print(
        "Refreshing monthly sales cache..."
    )

    with get_connection() as connection:
        connection.execute(
            """
            REFRESH MATERIALIZED VIEW
            reporting.monthly_sales_summary
            """
        )

        connection.execute(
            """
            ANALYZE warehouse.fact_sales
            """
        )

    with get_connection() as connection:
        row_count, net_revenue = (
            connection.execute(
                """
                SELECT
                    COUNT(*),
                    ROUND(
                        SUM(net_revenue),
                        2
                    )
                FROM
                reporting.monthly_sales_summary
                """
            ).fetchone()
        )

    print("CACHE REFRESH COMPLETED")
    print(f"Cached rows: {row_count:,}")
    print(f"Net revenue: {net_revenue:,}")


if __name__ == "__main__":
    main()