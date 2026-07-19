from src.config import SQL_DIRECTORY
from src.database import get_connection


def main() -> None:
    sql_files = sorted(SQL_DIRECTORY.glob("*.sql"))

    if not sql_files:
        raise FileNotFoundError(
            f"No SQL files found inside {SQL_DIRECTORY}"
        )

    print("Connecting to PostgreSQL...")

    with get_connection(autocommit=True) as connection:
        for sql_file in sql_files:
            print(f"Applying {sql_file.name}...")

            sql_code = sql_file.read_text(
                encoding="utf-8"
            )

            connection.execute(sql_code)

    print("Database setup completed successfully.")


if __name__ == "__main__":
    main()