from pathlib import Path
import hashlib
import uuid

import pandas as pd

from src.config import DATA_FILE
from src.database import get_connection


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
    """Calculate the source-file checksum."""
    file_hash = hashlib.sha256()

    with file_path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            file_hash.update(chunk)

    return file_hash.hexdigest()


def read_raw_csv(file_path: Path) -> pd.DataFrame:
    """
    Read every source column as text.

    Empty values are kept as empty strings because this is
    the immutable raw layer.
    """
    dataframe = pd.read_csv(
        file_path,
        encoding="ISO-8859-1",
        dtype="string",
        keep_default_na=False,
        na_filter=False,
    )

    if dataframe.columns.tolist() != EXPECTED_COLUMNS:
        raise ValueError(
            "Unexpected CSV schema.\n"
            f"Expected: {EXPECTED_COLUMNS}\n"
            f"Received: {dataframe.columns.tolist()}"
        )

    return dataframe


def register_source_file(
    source_hash: str,
    row_count: int,
) -> tuple[str, str]:
    """
    Register the source version.

    Returns:
        batch_id
        current status
    """
    with get_connection() as connection:
        existing_source = connection.execute(
            """
            SELECT
                batch_id::TEXT,
                status
            FROM audit.source_files
            WHERE sha256 = %s
            """,
            (source_hash,),
        ).fetchone()

        if existing_source:
            return existing_source[0], existing_source[1]

        batch_id = str(uuid.uuid4())

        connection.execute(
            """
            INSERT INTO audit.source_files (
                batch_id,
                source_file_name,
                source_file_path,
                sha256,
                file_size_bytes,
                row_count,
                status
            )
            VALUES (
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                'REGISTERED'
            )
            """,
            (
                batch_id,
                DATA_FILE.name,
                str(DATA_FILE.resolve()),
                source_hash,
                DATA_FILE.stat().st_size,
                row_count,
            ),
        )

        return batch_id, "REGISTERED"


def load_raw_data(
    dataframe: pd.DataFrame,
    batch_id: str,
) -> int:
    """
    Load source rows into PostgreSQL using COPY.

    CSV row 1 contains the headers, so data starts at
    source row number 2.
    """
    copy_statement = """
        COPY raw.online_retail (
            batch_id,
            source_row_number,
            invoice_no,
            stock_code,
            description,
            quantity,
            invoice_date,
            unit_price,
            customer_id,
            country
        )
        FROM STDIN
    """

    with get_connection() as connection:
        # Makes a retry safe if a previous attempt failed.
        connection.execute(
            """
            DELETE FROM raw.online_retail
            WHERE batch_id = %s
            """,
            (batch_id,),
        )

        with connection.cursor() as cursor:
            with cursor.copy(copy_statement) as copy:
                for source_row_number, row in enumerate(
                    dataframe.itertuples(
                        index=False,
                        name=None,
                    ),
                    start=2,
                ):
                    copy.write_row(
                        (
                            batch_id,
                            source_row_number,
                            *row,
                        )
                    )

        connection.execute(
            """
            UPDATE audit.source_files
            SET
                status = 'RAW_LOADED',
                row_count = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE batch_id = %s
            """,
            (
                len(dataframe),
                batch_id,
            ),
        )

    return len(dataframe)


def mark_source_failed(batch_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE audit.source_files
            SET
                status = 'FAILED',
                updated_at = CURRENT_TIMESTAMP
            WHERE batch_id = %s
            """,
            (batch_id,),
        )


def main() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    print(f"Reading source: {DATA_FILE}")

    dataframe = read_raw_csv(DATA_FILE)

    print(f"Source rows: {len(dataframe):,}")

    source_hash = calculate_sha256(DATA_FILE)

    print(f"SHA-256: {source_hash}")

    batch_id, current_status = register_source_file(
        source_hash,
        len(dataframe),
    )

    print(f"Batch ID: {batch_id}")
    print(f"Current status: {current_status}")

    if current_status in {
    "RAW_LOADED",
    "TRANSFORMED",
    "WAREHOUSE_LOADED",
    "SUCCESS",
    }:
        print(
            "This exact source version was already loaded. "
            "No rows were duplicated."
        )
        return

    try:
        print("Loading source rows into raw.online_retail...")

        loaded_rows = load_raw_data(
            dataframe,
            batch_id,
        )

    except Exception:
        mark_source_failed(batch_id)
        raise

    with get_connection() as connection:
        database_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM raw.online_retail
            WHERE batch_id = %s
            """,
            (batch_id,),
        ).fetchone()[0]

    print("------------------------------")
    print("RAW INGESTION COMPLETED")
    print("------------------------------")
    print(f"Rows loaded:    {loaded_rows:,}")
    print(f"Database rows:  {database_count:,}")
    print("Status:         RAW_LOADED")
    print("------------------------------")


if __name__ == "__main__":
    main()