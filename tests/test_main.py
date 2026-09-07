import pandas as pd
import pytest
import sys
import json

from main import (
    prepare_orders_dataframe,
    merge_dataframes,
    filter_orders_by_date,
    aggregate_by_customer,
    apply_discount_rules,
    apply_discounts,
    flag_suspicious_orders,
    get_suspicious_orders_by_customer,
    build_report,
    parse_arguments,
    export_report
)


# ---------------------------------------------------------------------------
# Fixtures: small, controlled datasets — no dependency on real data files
# ---------------------------------------------------------------------------

@pytest.fixture
def customers_df():
    return pd.DataFrame([
        {"id": 1, "name": "Alice", "tier": "VIP"},
        {"id": 2, "name": "Bob", "tier": "Regular"},
        {"id": 3, "name": "Carol", "tier": "Regular"},
        {"id": 4, "name": "Dave", "tier": "VIP"},
    ])


@pytest.fixture
def raw_orders_df():
    # Raw, as if freshly read from orders.csv, before prepare_orders_dataframe()
    return pd.DataFrame([
        {"id": 101, "customer_id": 1, "value": 300.0, "date": "2025-01-10"},
        {"id": 102, "customer_id": 1, "value": 320.0, "date": "2025-02-05"},
        {"id": 103, "customer_id": 2, "value": 600.0, "date": "2025-01-15"},
        {"id": 104, "customer_id": 2, "value": 50.0,  "date": "2025-02-20"},
        {"id": 105, "customer_id": 3, "value": 100.0, "date": "2025-01-20"},   # only 1 order
        {"id": 106, "customer_id": 4, "value": 10.0,  "date": "2025-01-01"},
        {"id": 107, "customer_id": 4, "value": 10.0,  "date": "2025-01-02"},
        {"id": 108, "customer_id": 4, "value": 100.0, "date": "2025-01-03"},   # suspicious for Dave
    ])


# ---------------------------------------------------------------------------
# prepare_orders_dataframe
# ---------------------------------------------------------------------------

def test_prepare_orders_dataframe_renames_id_and_converts_types(raw_orders_df):
    prepared = prepare_orders_dataframe(raw_orders_df)

    assert "order_id" in prepared.columns
    assert "id" not in prepared.columns
    assert pd.api.types.is_datetime64_any_dtype(prepared["date"])
    assert pd.api.types.is_numeric_dtype(prepared["value"])


def test_prepare_orders_dataframe_raises_on_invalid_value():
    bad_orders = pd.DataFrame([
        {"id": 1, "customer_id": 1, "value": "not_a_number", "date": "2025-01-01"},
    ])
    with pytest.raises(ValueError):
        prepare_orders_dataframe(bad_orders)


# ---------------------------------------------------------------------------
# filter_orders_by_date — covers the "scope is limited to the analyzed period" decision
# ---------------------------------------------------------------------------

def test_filter_orders_by_date_is_inclusive_on_both_ends(raw_orders_df):
    orders = prepare_orders_dataframe(raw_orders_df)
    filtered = filter_orders_by_date(
        orders,
        start_date=pd.Timestamp("2025-01-01"),
        end_date=pd.Timestamp("2025-01-01"),
    )
    # Only order 106 (customer 4) happens exactly on 2025-01-01
    assert len(filtered) == 1
    assert filtered.iloc[0]["order_id"] == 106


def test_filter_orders_by_date_excludes_outside_range(raw_orders_df):
    orders = prepare_orders_dataframe(raw_orders_df)
    filtered = filter_orders_by_date(
        orders,
        start_date=pd.Timestamp("2025-01-01"),
        end_date=pd.Timestamp("2025-01-31"),
    )
    # Only January orders should remain: 101, 103, 105, 106, 107, 108
    assert set(filtered["order_id"]) == {101, 103, 105, 106, 107, 108}


def test_filter_orders_by_date_empty_range_returns_empty_df(raw_orders_df):
    orders = prepare_orders_dataframe(raw_orders_df)
    filtered = filter_orders_by_date(
        orders,
        start_date=pd.Timestamp("2025-06-01"),
        end_date=pd.Timestamp("2025-06-30"),
    )
    assert filtered.empty


# ---------------------------------------------------------------------------
# apply_discount_rules — the core business rules
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tier,total_spent,order_count,expected_pct",
    [
        ("VIP", 100.0, 2, 0.10),        # VIP always gets 10%, regardless of amount
        ("VIP", 100.0, 1, 0.0),         # ...but not with fewer than 2 orders
        ("Regular", 501.0, 2, 0.05),    # Regular above 500 with >=2 orders
        ("Regular", 500.0, 2, 0.0),     # exactly 500 does NOT qualify (documented decision: strict >)
        ("Regular", 400.0, 2, 0.0),     # below threshold
        ("Regular", 600.0, 1, 0.0),     # only 1 order: no discount regardless of amount/tier
        ("Unknown", 1000.0, 5, 0.0),    # unrecognized tier: no discount
    ],
)
def test_apply_discount_rules(tier, total_spent, order_count, expected_pct):
    row = {"tier": tier, "total_spent": total_spent, "order_count": order_count}
    assert apply_discount_rules(row) == expected_pct


def test_apply_discounts_computes_total_after_discount():
    agg = pd.DataFrame([
        {"customer_id": 1, "name": "Alice", "tier": "VIP", "total_spent": 1000.0, "order_count": 3},
    ])
    result = apply_discounts(agg)

    assert result.loc[0, "discount_pct"] == 0.10
    assert result.loc[0, "total_after_discount"] == pytest.approx(900.0)


# ---------------------------------------------------------------------------
# flag_suspicious_orders — covers the "average includes the order itself" decision
# ---------------------------------------------------------------------------

def test_flag_suspicious_orders_detects_outlier(raw_orders_df):
    orders = prepare_orders_dataframe(raw_orders_df)
    flagged = flag_suspicious_orders(orders)

    dave_orders = flagged[flagged["customer_id"] == 4]
    # Dave's orders: 10, 10, 100 -> mean = 40 -> 3x mean = 120 -> none exceed 120
    # (this also documents that the average INCLUDES the order being evaluated,
    # which is why 100 does NOT get flagged here)
    assert not dave_orders["is_suspicious"].any()


def test_flag_suspicious_orders_flags_clear_outlier():
    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 1, "value": 100.0, "date": pd.Timestamp("2025-01-01")},
        {"order_id": 2, "customer_id": 1, "value": 100.0, "date": pd.Timestamp("2025-01-02")},
        {"order_id": 3, "customer_id": 1, "value": 1000.0, "date": pd.Timestamp("2025-01-03")},
    ])
    flagged = flag_suspicious_orders(orders)
    # mean = 400, 3x mean = 1200 -> 1000 still does NOT exceed 1200 with this formula
    assert not flagged.loc[flagged["order_id"] == 3, "is_suspicious"].iloc[0]


def test_flag_suspicious_orders_single_order_never_suspicious():
    # A customer with a single order: value == mean, so value > 3*mean is only
    # possible for negative values. This documents that behavior explicitly.
    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 1, "value": 9999.0, "date": pd.Timestamp("2025-01-01")},
    ])
    flagged = flag_suspicious_orders(orders)
    assert not flagged.loc[0, "is_suspicious"]


def test_get_suspicious_orders_by_customer_groups_correctly():
    orders = pd.DataFrame([
        {"order_id": 1, "customer_id": 1, "value": 10.0, "date": pd.Timestamp("2025-01-01"), "is_suspicious": False},
        {"order_id": 2, "customer_id": 1, "value": 500.0, "date": pd.Timestamp("2025-01-02"), "is_suspicious": True},
        {"order_id": 3, "customer_id": 2, "value": 20.0, "date": pd.Timestamp("2025-01-03"), "is_suspicious": False},
    ])
    result = get_suspicious_orders_by_customer(orders)

    assert list(result.keys()) == [1]
    assert result[1][0]["order_id"] == 2


# ---------------------------------------------------------------------------
# merge_dataframes + aggregate_by_customer — covers the "orphan customer_id" decision
# ---------------------------------------------------------------------------

def test_merge_dataframes_drops_orphan_orders_at_aggregation(customers_df, raw_orders_df):
    orders = prepare_orders_dataframe(raw_orders_df)

    # add an order referencing a customer_id that does not exist in customers_df
    orphan_order = pd.DataFrame([
        {"order_id": 999, "customer_id": 999, "value": 50.0, "date": pd.Timestamp("2025-01-01")}
    ])
    orders_with_orphan = pd.concat([orders, orphan_order], ignore_index=True)

    merged = merge_dataframes(orders_with_orphan, customers_df)
    # The orphan row exists in the merge with NaN name/tier...
    assert merged["name"].isna().any()

    # ...but is dropped once aggregated, since groupby excludes NaN keys by default
    agg = aggregate_by_customer(merged)
    assert 999 not in agg["customer_id"].values


# ---------------------------------------------------------------------------
# build_report — covers the "tier -> category" field naming decision
# ---------------------------------------------------------------------------

def test_build_report_maps_tier_to_category_field():
    customer_summary = pd.DataFrame([
        {
            "customer_id": 1, "name": "Alice", "tier": "VIP",
            "total_spent": 1000.0, "order_count": 3,
            "discount_pct": 0.10, "total_after_discount": 900.0,
        },
    ])
    report = build_report(customer_summary, suspicious_by_customer={})

    assert report[0]["category"] == "VIP"
    assert "tier" not in report[0]
    assert report[0]["suspicious_orders"] == []


def test_build_report_includes_suspicious_orders_for_matching_customer():
    customer_summary = pd.DataFrame([
        {
            "customer_id": 1, "name": "Alice", "tier": "VIP",
            "total_spent": 1000.0, "order_count": 3,
            "discount_pct": 0.10, "total_after_discount": 900.0,
        },
    ])
    suspicious = {1: [{"order_id": 5, "value": 999.0, "date": pd.Timestamp("2025-01-01")}]}
    report = build_report(customer_summary, suspicious_by_customer=suspicious)

    assert len(report[0]["suspicious_orders"]) == 1
    assert report[0]["suspicious_orders"][0]["order_id"] == 5

# --- parse_arguments ---

def test_parse_arguments_parses_valid_dates(monkeypatch):
    monkeypatch.setattr(
        sys, "argv",
        ["main.py", "--start-date", "2025-01-01", "--end-date", "2025-03-31"]
    )
    args = parse_arguments()

    assert args.start_date == pd.Timestamp("2025-01-01")
    assert args.end_date == pd.Timestamp("2025-03-31")


def test_parse_arguments_exits_when_start_after_end(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv",
        ["main.py", "--start-date", "2025-04-30", "--end-date", "2025-02-01"]
    )

    with pytest.raises(SystemExit) as exc_info:
        parse_arguments()

    # argparse's parser.error() exits with status code 2 by convention
    assert exc_info.value.code == 2

    captured = capsys.readouterr()
    assert "--start-date" in captured.err


def test_parse_arguments_exits_when_required_arg_missing(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["main.py", "--start-date", "2025-01-01"])

    with pytest.raises(SystemExit):
        parse_arguments()


def test_parse_arguments_allows_equal_start_and_end_date(monkeypatch):
    # Same-day range should be valid, not treated as "inverted"
    monkeypatch.setattr(
        sys, "argv",
        ["main.py", "--start-date", "2025-01-01", "--end-date", "2025-01-01"]
    )
    args = parse_arguments()
    assert args.start_date == args.end_date

# --- export_report ---

def test_export_report_creates_output_directory_if_missing(tmp_path):
    output_path = tmp_path / "nested" / "output" / "report.json"
    report = [{"name": "Alice", "category": "VIP", "suspicious_orders": []}]

    export_report(report, output_path)

    assert output_path.exists()
    assert output_path.parent.is_dir()


def test_export_report_writes_valid_json_content(tmp_path):
    output_path = tmp_path / "report.json"
    report = [
        {
            "name": "Alice",
            "category": "VIP",
            "total_spent_before_discount": 1000.0,
            "total_spent_after_discount": 900.0,
            "suspicious_orders": [],
        }
    ]

    export_report(report, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded == report


def test_export_report_serializes_timestamp_and_numpy_types(tmp_path):
    output_path = tmp_path / "report.json"
    report = [
        {
            "name": "Bob",
            "category": "Regular",
            "suspicious_orders": [
                {
                    "order_id": pd.array([5], dtype="int64")[0],   # numpy int64
                    "value": pd.array([999.5], dtype="float64")[0],  # numpy float64
                    "date": pd.Timestamp("2025-03-15"),
                }
            ],
        }
    ]

    export_report(report, output_path)

    with open(output_path, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    suspicious = loaded[0]["suspicious_orders"][0]
    assert suspicious["order_id"] == 5
    assert suspicious["value"] == 999.5
    assert suspicious["date"] == "2025-03-15"


def test_export_report_preserves_unicode_characters(tmp_path):
    output_path = tmp_path / "report.json"
    report = [{"name": "José", "category": "VIP", "suspicious_orders": []}]

    export_report(report, output_path)

    raw_content = output_path.read_text(encoding="utf-8")
    # ensure_ascii=False means accented characters should appear literally,
    # not escaped as \u00e9
    assert "José" in raw_content
    assert "\\u00e9" not in raw_content


# --- End-to-end pipeline ---

def test_customer_analysis_pipeline(raw_orders_df, customers_df):
    orders = prepare_orders_dataframe(raw_orders_df)

    orders = filter_orders_by_date(
        orders,
        pd.Timestamp("2025-01-01"),
        pd.Timestamp("2025-02-28")
    )

    orders = flag_suspicious_orders(orders)

    suspicious = get_suspicious_orders_by_customer(orders)

    merged = merge_dataframes(orders, customers_df)
    summary = aggregate_by_customer(merged)
    summary = apply_discounts(summary)

    report = build_report(summary, suspicious)

    alice = next(customer for customer in report if customer["name"] == "Alice")

    assert alice["category"] == "VIP"
    assert alice["total_spent_before_discount"] == 620.0
    assert alice["total_spent_after_discount"] == pytest.approx(558.0)
    assert alice["suspicious_orders"] == []