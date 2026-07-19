import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone

from src.alerts import emit_alert
from src.config import DATA_FILE, PROJECT_ROOT
from src.database import get_connection
from src.ingest_raw import calculate_sha256


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


class StepExecutionError(RuntimeError):
    def __init__(
        self,
        step_name: str,
        return_code: int,
    ) -> None:
        super().__init__(
            f"Step failed: {step_name} "
            f"(exit code {return_code})"
        )
        self.step_name = step_name
        self.return_code = return_code


def create_run(run_id: str) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO audit.etl_runs (
                run_id,
                status,
                current_stage
            )
            VALUES (
                %s,
                'RUNNING',
                'Pipeline initialization'
            )
            """,
            (run_id,),
        )


def update_run(
    run_id: str,
    *,
    status: str | None = None,
    current_stage: str | None = None,
    batch_id: str | None = None,
    finished: bool = False,
    error_message: str | None = None,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE audit.etl_runs
            SET
                status = COALESCE(%s, status),
                current_stage = COALESCE(
                    %s,
                    current_stage
                ),
                batch_id = COALESCE(
                    %s::UUID,
                    batch_id
                ),
                finished_at = CASE
                    WHEN %s
                    THEN CURRENT_TIMESTAMP
                    ELSE finished_at
                END,
                error_message = COALESCE(
                    %s,
                    error_message
                )
            WHERE run_id = %s
            """,
            (
                status,
                current_stage,
                batch_id,
                finished,
                error_message,
                run_id,
            ),
        )


def update_source_status(
    batch_id: str,
    status: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            UPDATE audit.source_files
            SET
                status = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE batch_id = %s
            """,
            (status, batch_id),
        )


def find_current_batch() -> str:
    source_hash = calculate_sha256(DATA_FILE)

    with get_connection() as connection:
        source = connection.execute(
            """
            SELECT batch_id::TEXT
            FROM audit.source_files
            WHERE sha256 = %s
            """,
            (source_hash,),
        ).fetchone()

    if not source:
        raise RuntimeError(
            "The ingested source batch could not be found."
        )

    return source[0]


def run_step(
    step_name: str,
    module_name: str,
    environment: dict[str, str],
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
        env=environment,
    )

    if result.stdout:
        print(result.stdout)
        logging.info(result.stdout.rstrip())

    if result.stderr:
        logging.error(result.stderr.rstrip())

    if result.returncode != 0:
        raise StepExecutionError(
            step_name,
            result.returncode,
        )

    logging.info(
        "Completed step: %s",
        step_name,
    )


def main() -> None:
    started_at = datetime.now(
        timezone.utc
    )
    run_id = str(uuid.uuid4())
    batch_id: str | None = None
    current_step = "Pipeline initialization"

    print("==============================")
    print("ONLINE RETAIL ETL PIPELINE")
    print("==============================")
    print(f"Run ID:  {run_id}")
    print(f"Started: {started_at.isoformat()}")

    environment = os.environ.copy()
    environment["ETL_RUN_ID"] = run_id

    try:
        create_run(run_id)

        for step_name, module_name in STEPS:
            current_step = step_name

            update_run(
                run_id,
                current_stage=step_name,
                batch_id=batch_id,
            )

            run_step(
                step_name,
                module_name,
                environment,
            )

            if step_name == "Raw ingestion":
                batch_id = find_current_batch()
                environment["ETL_BATCH_ID"] = batch_id

                update_run(
                    run_id,
                    batch_id=batch_id,
                )

        if batch_id:
            update_source_status(
                batch_id,
                "SUCCESS",
            )

        update_run(
            run_id,
            status="SUCCESS",
            current_stage="Completed",
            batch_id=batch_id,
            finished=True,
        )

    except Exception as error:
        logging.exception(
            "ETL pipeline failed during %s.",
            current_step,
        )

        alert_message = (
            f"ETL run {run_id} failed during "
            f"'{current_step}': {error}"
        )

        emit_alert(alert_message)

        if batch_id:
            try:
                update_source_status(
                    batch_id,
                    "FAILED",
                )
            except Exception:
                logging.exception(
                    "Could not update audit.source_files "
                    "after the pipeline failure."
                )

        try:
            update_run(
                run_id,
                status="FAILED",
                current_stage=current_step,
                batch_id=batch_id,
                finished=True,
                error_message=str(error),
            )
        except Exception:
            logging.exception(
                "Could not update audit.etl_runs "
                "after the pipeline failure."
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
