import re
from datetime import datetime, timezone

from src.config import PROJECT_ROOT
from src.database import get_connection


QUERIES = {
    "Invoice lookup": """
        SELECT
            invoice_no,
            invoice_timestamp,
            quantity,
            unit_price
        FROM warehouse.fact_sales
        WHERE invoice_no = '536365'
    """,

    "November partition query": """
        SELECT
            country_key,
            SUM(line_amount)
                AS net_revenue
        FROM warehouse.fact_sales
        WHERE
            invoice_date
                >= DATE '2011-11-01'
            AND invoice_date
                < DATE '2011-12-01'
        GROUP BY country_key
    """,

    "Base fact aggregation": """
        SELECT
            date_trunc(
                'month',
                invoice_date
            )::DATE AS sales_month,
            country_key,
            SUM(line_amount)
                AS net_revenue
        FROM warehouse.fact_sales
        GROUP BY
            sales_month,
            country_key
        ORDER BY
            sales_month,
            country_key
    """,

    "Materialized cache query": """
        SELECT
            sales_month,
            country_key,
            net_revenue
        FROM
            reporting.monthly_sales_summary
        ORDER BY
            sales_month,
            country_key
    """,
}


def explain_query(
    connection,
    query: str,
) -> tuple[str, float | None]:
    rows = connection.execute(
        """
        EXPLAIN (
            ANALYZE,
            BUFFERS,
            FORMAT TEXT
        )
        """
        + query
    ).fetchall()

    plan = "\n".join(
        row[0]
        for row in rows
    )

    match = re.search(
        r"Execution Time: ([0-9.]+) ms",
        plan,
    )

    execution_time = (
        float(match.group(1))
        if match
        else None
    )

    return plan, execution_time


def main() -> None:
    report_sections = [
        "# Query Performance Report",
        "",
        "Generated at: "
        + datetime.now(
            timezone.utc
        ).isoformat(),
        "",
        (
            "Timings depend on hardware. "
            "The execution-plan shape is "
            "the primary evidence."
        ),
        "",
    ]

    with get_connection() as connection:
        connection.execute(
            """
            ANALYZE warehouse.fact_sales
            """
        )

        for name, query in QUERIES.items():
            plan, execution_time = (
                explain_query(
                    connection,
                    query,
                )
            )

            report_sections.extend(
                [
                    f"## {name}",
                    "",
                    (
                        "Execution time: "
                        f"{execution_time} ms"
                    ),
                    "",
                    "```text",
                    plan,
                    "```",
                    "",
                ]
            )

    report_file = (
        PROJECT_ROOT
        / "reports"
        / "performance_report.md"
    )

    report_file.write_text(
        "\n".join(report_sections),
        encoding="utf-8",
    )

    print(
        "Performance report written to:"
    )
    print(report_file)


if __name__ == "__main__":
    main()