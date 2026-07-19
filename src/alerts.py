import json
import urllib.request
from datetime import datetime, timezone

from src.config import (
    ALERT_WEBHOOK_URL,
    PROJECT_ROOT,
)


def emit_alert(message: str) -> None:
    log_directory = PROJECT_ROOT / "logs"

    log_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    alert_file = (
        log_directory / "alerts.log"
    )

    timestamp = datetime.now(
        timezone.utc
    ).isoformat()

    with alert_file.open(
        "a",
        encoding="utf-8",
    ) as file:
        file.write(
            f"{timestamp} | {message}\n"
        )

    print(f"ALERT: {message}")

    if not ALERT_WEBHOOK_URL:
        return

    payload = json.dumps(
        {"text": message}
    ).encode("utf-8")

    request = urllib.request.Request(
        ALERT_WEBHOOK_URL,
        data=payload,
        headers={
            "Content-Type": "application/json"
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10,
        ):
            pass
    except Exception as error:
        print(
            "Webhook delivery failed: "
            f"{error}"
        )