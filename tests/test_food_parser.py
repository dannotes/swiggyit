"""Tests for src/parser/food_parser.py."""

import pytest

from parser.food_parser import _parse_float, _parse_header, _parse_tax_block, _parse_eco_block


class TestParseFloat:
    def test_normal(self):
        assert _parse_float("1,774.50") == 1774.50

    def test_rupee_symbol(self):
        assert _parse_float("₹500.00") == 500.0

    def test_empty(self):
        assert _parse_float("") == 0.0

    def test_none_like(self):
        assert _parse_float("") == 0.0

    def test_bad_value(self):
        assert _parse_float("N/A") == 0.0

    def test_zero(self):
        assert _parse_float("0") == 0.0

    def test_no_decimal(self):
        assert _parse_float("1000") == 1000.0

    def test_whitespace(self):
        assert _parse_float("  500.50  ") == 500.50


class TestParseHeader:
    SAMPLE_HEADER = (
        "Invoice To: Dan Ny  Invoice issued by:\n"
        "GSTIN: URP\n"
        "Customer Address: 123 Main St  Restaurant GSTIN: 29AABCT1234Z1\n"
        "Order ID: 123456789012345\n"
        "Document: INV\n"
        "Invoice No: S-INV-2025-001\n"
        "Date of Invoice: 15-01-2025\n"
        "HSN Code: 996331\n"
        "Restaurant Name: Test Kitchen\n"
        "Restaurant GSTIN: 29AABCT1234Z1\n"
        "Restaurant FSSAI License: 11234567890123\n"
        "Address: Plot 1, MG Road\n"
        "State: Karnataka\n"
        "Place of Supply: Karnataka\n"
        "Service Description: Restaurant Service\n"
        "Category: B2C\n"
        "Reverse Charges Applicable: No\n"
    )

    def test_order_id(self):
        h = _parse_header(self.SAMPLE_HEADER)
        assert h["order_id"] == "123456789012345"

    def test_restaurant_name(self):
        h = _parse_header(self.SAMPLE_HEADER)
        assert h["restaurant_name"] == "Test Kitchen"

    def test_date(self):
        h = _parse_header(self.SAMPLE_HEADER)
        assert h["date_of_invoice"] == "15-01-2025"

    def test_invoice_no(self):
        h = _parse_header(self.SAMPLE_HEADER)
        assert h["invoice_no"] == "S-INV-2025-001"

    def test_document_type(self):
        h = _parse_header(self.SAMPLE_HEADER)
        assert h["document_type"] == "INV"

    def test_state(self):
        h = _parse_header(self.SAMPLE_HEADER)
        assert h["restaurant_state"] == "Karnataka"

    def test_empty_header(self):
        h = _parse_header("")
        assert h["order_id"] == ""
        assert h["restaurant_name"] == ""


class TestParseTaxBlock:
    SAMPLE_TAX = (
        "Taxes and charges:\n"
        "CGST 2.5% 12.50\n"
        "SGST/UTGST 2.5% 12.50\n"
        "IGST 0.0% 0.00\n"
        "Total taxes 25.00\n"
        "Invoice Total 525.00\n"
    )

    def test_cgst(self):
        t = _parse_tax_block(self.SAMPLE_TAX)
        assert t["cgst_rate"] == 2.5
        assert t["cgst_amount"] == 12.50

    def test_sgst(self):
        t = _parse_tax_block(self.SAMPLE_TAX)
        assert t["sgst_rate"] == 2.5
        assert t["sgst_amount"] == 12.50

    def test_totals(self):
        t = _parse_tax_block(self.SAMPLE_TAX)
        assert t["total_taxes"] == 25.0
        assert t["invoice_total"] == 525.0

    def test_empty(self):
        t = _parse_tax_block("")
        assert t["cgst_rate"] == 0.0
        assert t["invoice_total"] == 0.0


class TestParseEcoBlock:
    SAMPLE_ECO = (
        "E-Commerce Operator (ECO under GST)\n"
        "Name: Bundl Technologies Private Limited\n"
        "Address: Tower D, 9th Floor, IBC Knowledge Park\n"
        "GSTIN: 29AABCB1234Z1\n"
        "Swiggy FSSAI: 11223344556677\n"
    )

    def test_name(self):
        eco = _parse_eco_block(self.SAMPLE_ECO)
        assert eco["eco_name"] == "Bundl Technologies Private Limited"

    def test_gstin(self):
        eco = _parse_eco_block(self.SAMPLE_ECO)
        assert eco["eco_gstin"] == "29AABCB1234Z1"

    def test_fssai(self):
        eco = _parse_eco_block(self.SAMPLE_ECO)
        assert eco["eco_fssai"] == "11223344556677"

    def test_empty(self):
        eco = _parse_eco_block("")
        assert eco["eco_name"] == ""
        assert eco["eco_gstin"] == ""
