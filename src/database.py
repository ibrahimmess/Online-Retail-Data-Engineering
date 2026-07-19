from collections.abc import Iterable
from typing import Any

import pandas as pd
import psycopg
from psycopg import sql

from src.config import DATABASE_URL


def get_connection(*, autocommit: bool = False):
    return psycopg.connect(
        DATABASE_URL,
        autocommit=autocommit,
    )


def convert_to_python_value(value: Any) -> Any:
    """Convert pandas and NumPy values for PostgreSQL."""

    if value is None:
        return None

    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if hasattr(value, "item"):
        return value.item()

    return value


def copy_dataframe(
    connection,
    dataframe: pd.DataFrame,
    table_name: str,
    columns: Iterable[str],
) -> int:
    """Load a DataFrame efficiently with PostgreSQL COPY."""

    columns = list(columns)

    if dataframe.empty:
        return 0

    schema_name, relation_name = table_name.split(
        ".",
        maxsplit=1,
    )

    copy_statement = sql.SQL(
        "COPY {} ({}) FROM STDIN"
    ).format(
        sql.Identifier(
            schema_name,
            relation_name,
        ),
        sql.SQL(", ").join(
            map(sql.Identifier, columns)
        ),
    )

    with connection.cursor() as cursor:
        with cursor.copy(copy_statement) as copy:
            for row in dataframe[columns].itertuples(
                index=False,
                name=None,
            ):
                copy.write_row(
                    tuple(
                        convert_to_python_value(value)
                        for value in row
                    )
                )

    return len(dataframe)