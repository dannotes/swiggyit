"""Tests for src/parser/instamart_parser.py."""

import pytest

from parser.instamart_parser import (
    _pf,
    _parse_seller_header,
    _parse_handling_header,
    _parse_handling_tax,
)


class TestPf:
    def test_normal(self):
        assert _pf("1,774.50") == 1774.50

    def test_rupee(self):
        assert _pf("₹500.00") == 500.0

    def test_empty(self):
        assert _pf("") == 0.0

    def test_bad(self):
        assert _pf("N/A") == 0.0

    def test_zero(self):
        assert _pf("0") == 0.0

    def test_none(self):
        assert _pf(None) == 0.0

    def test_whitespace(self):
        assert _pf("  123.45  ") == 123.45


class TestParseSellerHeader:
    SAMPLE = (
        "Invoice To: Dan Ny  Seller Name: Fresh Farms Pvt Ltd\n"
        "GSTIN: URP\n"
        "Customer Address: 123 Main St  FSSAI: 11234567890123\n"
        "Order ID: 220939704984728\n"
        "Address: Plot 5, Industrial Area\n"
        "City: Bangalore\n"
        "Document: INV\n"
        "Invoice No: INM-2025-001\n"
        "Date of Invoice: 15-01-2025\n"
        "Category: B2C\n"
        "State: Karnataka\n"
        "Place of Supply: Karnataka\n"
    )

    def test_order_id(self):
        d = _parse_seller_header(self.SAMPLE)
        assert d["order_id"] == "220939704984728"

    def test_seller_name(self):
        d = _parse_seller_header(self.SAMPLE)
        assert d["seller_name"] == "Fresh Farms Pvt Ltd"

    def test_date(self):
        d = _parse_seller_header(self.SAMPLE)
        assert d["date_of_invoice"] == "15-01-2025"

    def test_seller_city(self):
        d = _parse_seller_header(self.SAMPLE)
        assert d["seller_city"] == "Bangalore"

    def test_empty(self):
        d = _parse_seller_header("")
        assert d["order_id"] == ""
        assert d["seller_name"] == ""


class TestParseHandlingHeader:
    SAMPLE = (
        "PAN: AABCB1234A\n"
        "GSTIN: 29AABCB1234Z1\n"
        "Address: Tower D, IBC Knowledge Park\n"
        "Pincode: 560029\n"
        "State Code: 29\n"
        "Invoice No: HF-2025-001\n"
        "Date of Invoice: 15-01-2025\n"
        "Category: B2C\n"
        "Transaction Type: Regular\n"
        "Invoice Type: Regular\n"
        "Whether Reverse Charges No\n"
    )

    def test_pan(self):
        d = _parse_handling_header(self.SAMPLE)
        assert d["swiggy_pan"] == "AABCB1234A"

    def test_gstin(self):
        d = _parse_handling_header(self.SAMPLE)
        assert d["swiggy_gstin"] == "29AABCB1234Z1"

    def test_invoice_no(self):
        d = _parse_handling_header(self.SAMPLE)
        assert d["invoice_no"] == "HF-2025-001"

    def test_reverse_charges(self):
        d = _parse_handling_header(self.SAMPLE)
        assert d["reverse_charges"] == "No"

    def test_empty(self):
        d = _parse_handling_header("")
        assert d["swiggy_pan"] == ""


class TestParseHandlingTax:
    SAMPLE = (
        "996812 Handling charges for order 123\n"
        "CGST 9.0% 4.50\n"
        "SGST/UTGST 9.0% 4.50\n"
        "State CESS 0.0% 0.00\n"
        "Total taxes 9.00\n"
        "Invoice Total 59.00\n"
    )

    def test_cgst(self):
        t = _parse_handling_tax(self.SAMPLE)
        assert t["cgst_rate"] == 9.0
        assert t["cgst_amount"] == 4.50

    def test_sgst(self):
        t = _parse_handling_tax(self.SAMPLE)
        assert t["sgst_rate"] == 9.0
        assert t["sgst_amount"] == 4.50

    def test_totals(self):
        t = _parse_handling_tax(self.SAMPLE)
        assert t["total_taxes"] == 9.0
        assert t["invoice_total"] == 59.0

    def test_hsn(self):
        t = _parse_handling_tax(self.SAMPLE)
        assert t["hsn_code"] == "996812"

    def test_empty(self):
        t = _parse_handling_tax("")
        assert t["total_taxes"] == 0.0
        assert t["invoice_total"] == 0.0
