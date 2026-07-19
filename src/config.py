import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]

load_dotenv(PROJECT_ROOT / ".env")

DATABASE_URL = os.getenv("DATABASE_URL")
ALERT_WEBHOOK_URL = (
    os.getenv("ALERT_WEBHOOK_URL")
    or None
)
DATA_FILE = PROJECT_ROOT / "data" / "raw" / "online_retail.csv"

SQL_DIRECTORY = PROJECT_ROOT / "sql"


if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. "
        "Make sure the .env file exists at the project root."
    )