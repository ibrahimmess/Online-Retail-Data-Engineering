import logging
import subprocess
import sys
from datetime import datetime, timezone

from src.config import PROJECT_ROOT


LOG_DIRECTORY = PROJECT_ROOT / "logs"

LOG_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(message)s"
    ),
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(
            LOG_DIRECTORY / "etl.log",
            encoding="utf-8",
        ),
    ],
)


STEPS = [
    (
        "Raw ingestion",
        "src.ingest_raw",
    ),
    (
        "Dataset archiving",
        "src.archive_version",
    ),
    (
        "Cleaning and transformation",
        "src.transform_to_staging",
    ),
    (
        "Warehouse loading",
        "src.load_warehouse",
    ),
    (
        "Data-quality monitoring",
        "src.check_quality",
    ),
    (
        "Reporting-cache refresh",
        "src.refresh_cache",
    ),
]


def run_step(
    step_name: str,
    module_name: str,
) -> None:
    logging.info(
        "Starting step: %s",
        step_name,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            module_name,
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
    )

    if result.stdout:
        print(result.stdout)
        logging.info(result.stdout)

    if result.stderr:
        logging.error(result.stderr)

    if result.returncode != 0:
        raise RuntimeError(
            f"Step failed: {step_name}"
        )

    logging.info(
        "Completed step: %s",
        step_name,
    )


def main() -> None:
    started_at = datetime.now(
        timezone.utc
    )

    print("==============================")
    print("ONLINE RETAIL ETL PIPELINE")
    print("==============================")
    print(f"Started: {started_at.isoformat()}")

    try:
        for step_name, module_name in STEPS:
            run_step(
                step_name,
                module_name,
            )

    except Exception:
        logging.exception(
            "ETL pipeline failed."
        )
        raise

    finished_at = datetime.now(
        timezone.utc
    )

    print("==============================")
    print(
        "PIPELINE COMPLETED SUCCESSFULLY"
    )
    print(f"Finished: {finished_at.isoformat()}")
    print(
        "Duration: "
        f"{finished_at - started_at}"
    )
    print("==============================")


if __name__ == "__main__":
    main()