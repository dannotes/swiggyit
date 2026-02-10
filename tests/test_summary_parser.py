"""Tests for src/parser/summary_parser.py."""

import re

import pytest

from parser.summary_parser import (
    AMOUNT_PATTERN,
    DATE_PATTERN,
    ORDER_ID_PATTERN,
    _detect_order_type,
    _extract_header,
    _parse_amount,
)
from pathlib import Path


class TestParseAmount:
    def test_normal(self):
        assert _parse_amount("₹1,774.50") == 1774.50

    def test_no_comma(self):
        assert _parse_amount("₹500.00") == 500.0

    def test_large(self):
        assert _parse_amount("₹44,633.43") == 44633.43

    def test_no_rupee_symbol(self):
        assert _parse_amount("1774.50") == 1774.50

    def test_whitespace(self):
        assert _parse_amount("  ₹1,774.50  ") == 1774.50

    def test_zero(self):
        assert _parse_amount("₹0.00") == 0.0


class TestDetectOrderType:
    def test_food(self):
        assert _detect_order_type(Path("order_summary_food_123.pdf")) == "food"

    def test_instamart(self):
        assert _detect_order_type(Path("order_summary_instamart_456.pdf")) == "instamart"

    def test_unknown(self):
        with pytest.raises(ValueError, match="Cannot detect"):
            _detect_order_type(Path("order_summary_789.pdf"))

    def test_case_insensitive(self):
        assert _detect_order_type(Path("Order_Summary_FOOD_123.pdf")) == "food"


class TestExtractHeader:
    def test_full_header(self):
        lines = [
            "some preamble",
            "Customer Name",
            "Number of Orders",
            "Total Amount",
            "John Doe",
            "36",
            "₹44633.43",
            "Email",
            "Date Range",
            "john@example.com",
            "09-08-2025 to 09-02-2026",
        ]
        header = _extract_header(lines)
        assert header["customer_name"] == "John Doe"
        assert header["number_of_orders"] == 36
        assert header["total_amount"] == 44633.43
        assert header["customer_email"] == "john@example.com"
        assert header["date_range"] == "09-08-2025 to 09-02-2026"

    def test_missing_header(self):
        lines = ["no", "relevant", "data"]
        header = _extract_header(lines)
        assert header == {}


class TestRegexPatterns:
    def test_date_pattern_valid(self):
        assert DATE_PATTERN.match("09-08-2025")
        assert DATE_PATTERN.match("01-01-2026")

    def test_date_pattern_invalid(self):
        assert not DATE_PATTERN.match("2025-08-09")
        assert not DATE_PATTERN.match("9-8-2025")

    def test_order_id_pattern_valid(self):
        assert ORDER_ID_PATTERN.match("123456789012345")

    def test_order_id_pattern_invalid(self):
        assert not ORDER_ID_PATTERN.match("12345")
        assert not ORDER_ID_PATTERN.match("1234567890123456")
        assert not ORDER_ID_PATTERN.match("12345678901234a")

    def test_amount_pattern_valid(self):
        assert AMOUNT_PATTERN.match("₹1,774.50")
        assert AMOUNT_PATTERN.match("₹500")
        assert AMOUNT_PATTERN.match("₹44633.43")

    def test_amount_pattern_invalid(self):
        assert not AMOUNT_PATTERN.match("1774.50")
        assert not AMOUNT_PATTERN.match("Rs 1774")
