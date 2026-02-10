"""Tests for src/validator.py."""

import tempfile
from pathlib import Path

import pytest

from validator import (
    ValidationError,
    validate_date,
    validate_email,
    validate_invoice_fields,
    validate_order_id,
    validate_pdf_file,
    validate_summary_counts,
    validate_summary_folder,
)


class TestValidatePdfFile:
    def test_valid_pdf(self, tmp_path):
        pdf = tmp_path / "test.pdf"
        pdf.write_bytes(b"%PDF-1.4 fake content")
        validate_pdf_file(pdf)  # should not raise

    def test_missing_file(self, tmp_path):
        with pytest.raises(ValidationError, match="File not found"):
            validate_pdf_file(tmp_path / "nope.pdf")

    def test_empty_file(self, tmp_path):
        pdf = tmp_path / "empty.pdf"
        pdf.write_bytes(b"")
        with pytest.raises(ValidationError, match="Empty file"):
            validate_pdf_file(pdf)

    def test_bad_magic_bytes(self, tmp_path):
        pdf = tmp_path / "bad.pdf"
        pdf.write_bytes(b"<html>not a pdf</html>")
        with pytest.raises(ValidationError, match="Not a valid PDF"):
            validate_pdf_file(pdf)


class TestValidateSummaryFolder:
    def test_food_in_food_folder(self):
        validate_summary_folder("food", "food")  # should not raise

    def test_instamart_in_instamart_folder(self):
        validate_summary_folder("instamart", "instamart")  # should not raise

    def test_food_in_instamart_folder(self):
        with pytest.raises(ValidationError, match="Folder mismatch"):
            validate_summary_folder("instamart", "food")

    def test_instamart_in_food_folder(self):
        with pytest.raises(ValidationError, match="Folder mismatch"):
            validate_summary_folder("food", "instamart")


class TestValidateOrderId:
    def test_valid_15_digits(self):
        validate_order_id("123456789012345")  # should not raise

    def test_empty(self):
        with pytest.raises(ValidationError, match="Empty order_id"):
            validate_order_id("")

    def test_too_short(self):
        with pytest.raises(ValidationError, match="Invalid order_id"):
            validate_order_id("12345")

    def test_too_long(self):
        with pytest.raises(ValidationError, match="Invalid order_id"):
            validate_order_id("1234567890123456")

    def test_non_numeric(self):
        with pytest.raises(ValidationError, match="Invalid order_id"):
            validate_order_id("12345678901234a")

    def test_context_in_message(self):
        with pytest.raises(ValidationError, match="in food order"):
            validate_order_id("bad", "food order")


class TestValidateDate:
    def test_valid_date(self):
        assert validate_date("15-01-2025") == "2025-01-15"

    def test_valid_date_leap(self):
        assert validate_date("29-02-2024") == "2024-02-29"

    def test_empty(self):
        with pytest.raises(ValidationError, match="Empty date"):
            validate_date("")

    def test_bad_format(self):
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("2025-01-15")

    def test_invalid_date(self):
        with pytest.raises(ValidationError, match="Invalid date format"):
            validate_date("32-01-2025")

    def test_context_in_message(self):
        with pytest.raises(ValidationError, match="in food order"):
            validate_date("bad", "food order")


class TestValidateEmail:
    def test_valid_email(self, capsys):
        assert validate_email("user@example.com") is True
        assert capsys.readouterr().out == ""

    def test_empty_email(self, capsys):
        assert validate_email("") is False
        assert "Empty customer email" in capsys.readouterr().out

    def test_bad_format(self, capsys):
        assert validate_email("not-an-email") is False
        assert "Suspicious email" in capsys.readouterr().out

    def test_no_domain(self, capsys):
        assert validate_email("user@") is False


class TestValidateInvoiceFields:
    def _make_food_inv(self, **overrides):
        from types import SimpleNamespace
        defaults = {
            "order_id": "123456789012345",
            "date_of_invoice": "01-01-2025",
            "invoice_no": "INV001",
            "restaurant_name": "Test Restaurant",
            "invoice_total": 500.0,
            "items": [{"desc": "item"}],
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def _make_instamart_inv(self, **overrides):
        from types import SimpleNamespace
        defaults = {
            "order_id": "123456789012345",
            "date_of_invoice": "01-01-2025",
            "invoice_no": "INV001",
            "seller_name": "Test Seller",
            "invoice_value": 500.0,
            "items": [{"desc": "item"}],
        }
        defaults.update(overrides)
        return SimpleNamespace(**defaults)

    def test_valid_food(self):
        assert validate_invoice_fields(self._make_food_inv(), "food") is True

    def test_missing_restaurant(self, capsys):
        assert validate_invoice_fields(
            self._make_food_inv(restaurant_name=""), "food"
        ) is False
        assert "Missing restaurant_name" in capsys.readouterr().out

    def test_zero_total(self, capsys):
        assert validate_invoice_fields(
            self._make_food_inv(invoice_total=0), "food"
        ) is False

    def test_no_items(self, capsys):
        assert validate_invoice_fields(
            self._make_food_inv(items=[]), "food"
        ) is False

    def test_valid_instamart(self):
        assert validate_invoice_fields(self._make_instamart_inv(), "instamart") is True

    def test_missing_seller(self, capsys):
        assert validate_invoice_fields(
            self._make_instamart_inv(seller_name=""), "instamart"
        ) is False


class TestValidateSummaryCounts:
    def test_matching_counts(self):
        from types import SimpleNamespace
        s = SimpleNamespace(number_of_orders=3, orders=[1, 2, 3])
        assert validate_summary_counts(s) is True

    def test_mismatched_counts(self, capsys):
        from types import SimpleNamespace
        s = SimpleNamespace(number_of_orders=5, orders=[1, 2, 3])
        assert validate_summary_counts(s) is False
        assert "header says 5" in capsys.readouterr().out
