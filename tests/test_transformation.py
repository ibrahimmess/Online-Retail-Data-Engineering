import pandas as pd

from src.transform_to_staging import (
    transform_dataframe,
)


def make_raw(
    rows: list[list[str]],
) -> pd.DataFrame:
    columns = [
        "invoice_no",
        "stock_code",
        "description",
        "quantity",
        "invoice_date",
        "unit_price",
        "customer_id",
        "country",
    ]

    dataframe = pd.DataFrame(
        rows,
        columns=columns,
        dtype="string",
    )

    dataframe.insert(
        0,
        "source_row_number",
        range(2, len(dataframe) + 2),
    )

    return dataframe


def test_cancellation_is_preserved():
    raw = make_raw(
        [
            [
                "100",
                "12345",
                "Item",
                "2",
                "2011-01-01 10:00:00",
                "3.50",
                "1.0",
                "EIRE",
            ],
            [
                "C100",
                "12345",
                "Item",
                "-2",
                "2011-01-02 10:00:00",
                "3.50",
                "1.0",
                "EIRE",
            ],
        ]
    )

    result = transform_dataframe(
        raw,
        "test-batch",
    )

    assert len(result.clean) == 2

    cancellation = result.clean.loc[
        result.clean[
            "invoice_no"
        ].eq("C100")
    ].iloc[0]

    assert (
        cancellation["transaction_type"]
        == "CANCELLATION"
    )

    assert cancellation["quantity"] == -2

    assert set(result.clean["country"]) == {
        "Ireland"
    }


def test_negative_price_is_rejected():
    raw = make_raw(
        [
            [
                "A1",
                "B",
                "Bad debt",
                "1",
                "2011-01-01 10:00:00",
                "-5",
                "",
                "UK",
            ]
        ]
    )

    result = transform_dataframe(
        raw,
        "test-batch",
    )

    assert result.clean.empty
    assert result.metrics["rejected_rows"] == 1
    assert (
        result.exclusions.iloc[0]["reasons"]
        == "NEGATIVE_UNIT_PRICE"
    )


def test_missing_customer_is_kept():
    raw = make_raw(
        [
            [
                "100",
                "12345",
                "Item",
                "2",
                "2011-01-01 10:00:00",
                "3",
                "",
                "UK",
            ]
        ]
    )

    result = transform_dataframe(
        raw,
        "test-batch",
    )

    assert len(result.clean) == 1

    assert pd.isna(
        result.clean.iloc[0][
            "customer_id"
        ]
    )


def test_duplicate_is_excluded():
    row = [
        "100",
        "12345",
        "Item",
        "2",
        "2011-01-01 10:00:00",
        "3",
        "1",
        "UK",
    ]

    result = transform_dataframe(
        make_raw([row, row]),
        "test-batch",
    )

    assert len(result.clean) == 1

    assert (
        result.metrics["duplicate_rows"]
        == 1
    )


def test_description_is_recovered():
    raw = make_raw(
        [
            [
                "100",
                " 12345 ",
                "Blue item",
                "1",
                "2011-01-01 10:00:00",
                "3",
                "1",
                "UK",
            ],
            [
                "101",
                "12345",
                "",
                "1",
                "2011-01-01 11:00:00",
                "3",
                "2",
                "UK",
            ],
        ]
    )

    result = transform_dataframe(
        raw,
        "test-batch",
    )

    assert set(
        result.clean["description"]
    ) == {"BLUE ITEM"}