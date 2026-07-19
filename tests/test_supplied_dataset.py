import pandas as pd

from src.config import DATA_FILE
from src.transform_to_staging import (
    transform_dataframe,
)


def test_supplied_dataset_counts():
    raw = pd.read_csv(
        DATA_FILE,
        encoding="ISO-8859-1",
        dtype="string",
        keep_default_na=False,
        na_filter=False,
    )

    raw.columns = [
        "invoice_no",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "unit_price",
        "customer_id",
        "country",
    ]

    raw.insert(
        0,
        "source_row_number",
        range(2, len(raw) + 2),
    )

    result = transform_dataframe(
        raw,
        "test-batch",
    )

    assert len(raw) == 541_909

    assert (
        result.metrics["accepted_rows"]
        == 536_639
    )

    assert (
        result.metrics["rejected_rows"]
        == 2
    )

    assert (
        result.metrics["duplicate_rows"]
        == 5_268
    )

    assert (
        result.metrics["net_line_amount"]
        == 9_748_131.07
    )