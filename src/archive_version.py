import hashlib
import json
import shutil
from datetime import date, datetime, timezone

from src.config import (
    DATA_FILE,
    PROJECT_ROOT,
)
from src.database import get_connection


def calculate_sha256() -> str:
    file_hash = hashlib.sha256()

    with DATA_FILE.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            file_hash.update(chunk)

    return file_hash.hexdigest()


def main() -> None:
    source_hash = calculate_sha256()

    with get_connection() as connection:
        source = connection.execute(
            """
            SELECT
                batch_id::TEXT,
                source_version
            FROM audit.source_files
            WHERE sha256 = %s
            """,
            (source_hash,),
        ).fetchone()

    if not source:
        raise RuntimeError(
            "Source was not registered."
        )

    batch_id, source_version = source

    archive_directory = (
        PROJECT_ROOT
        / "data"
        / "archive"
        / date.today().isoformat()
        / source_hash
    )

    archive_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    archived_file = (
        archive_directory
        / DATA_FILE.name
    )

    if not archived_file.exists():
        shutil.copy2(
            DATA_FILE,
            archived_file,
        )

    archived_relative_path = archived_file.relative_to(
        PROJECT_ROOT
    ).as_posix()

    manifest = {
        "batch_id": batch_id,
        "source_version": source_version,
        "source_file": DATA_FILE.name,
        "sha256": source_hash,
        "file_size_bytes": (
            DATA_FILE.stat().st_size
        ),
        "pipeline_version": "1.0.0",
        "archived_at_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "archived_path": archived_relative_path,
    }

    manifest_file = (
        archive_directory
        / "manifest.json"
    )

    manifest_file.write_text(
        json.dumps(
            manifest,
            indent=2,
        ),
        encoding="utf-8",
    )

    with get_connection() as connection:
        connection.execute(
            """
            UPDATE audit.source_files
            SET
                archived_path = %s,
                pipeline_version = '1.0.0',
                updated_at = CURRENT_TIMESTAMP
            WHERE batch_id = %s
            """,
            (
                archived_relative_path,
                batch_id,
            ),
        )

    print("DATASET VERSION ARCHIVED")
    print(f"Source version: {source_version}")
    print(f"SHA-256: {source_hash}")
    print(f"Archive: {archived_file}")
    print(f"Manifest: {manifest_file}")


if __name__ == "__main__":
    main()