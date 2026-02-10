"""Integration tests — require actual PDFs in input/ and .tmp/ directories.

Run with: pytest tests/test_integration.py -v -m integration
"""

import pytest

from parser.summary_parser import parse_summary
from parser.food_parser import parse_food_detail
from parser.instamart_parser import parse_instamart_detail


@pytest.mark.integration
class TestFoodSummary:
    def test_parse_food_summary(self, input_food_dir):
        pdfs = list(input_food_dir.glob("order_summary_food_*.pdf"))
        assert len(pdfs) >= 1, "No food summary PDFs found"

        summary = parse_summary(pdfs[0])
        assert summary.order_type == "food"
        assert summary.number_of_orders == 36
        assert summary.customer_name
        assert len(summary.orders) == 36

    def test_food_order_ids_are_15_digits(self, input_food_dir):
        pdfs = list(input_food_dir.glob("order_summary_food_*.pdf"))
        summary = parse_summary(pdfs[0])

        for order in summary.orders:
            assert len(order.order_id) == 15
            assert order.order_id.isdigit()


@pytest.mark.integration
class TestInstamartSummary:
    def test_parse_instamart_summary(self, input_instamart_dir):
        pdfs = list(input_instamart_dir.glob("order_summary_instamart_*.pdf"))
        assert len(pdfs) >= 1, "No instamart summary PDFs found"

        summary = parse_summary(pdfs[0])
        assert summary.order_type == "instamart"
        assert summary.number_of_orders == 55
        assert len(summary.orders) == 55


@pytest.mark.integration
class TestFoodDetail:
    def test_parse_single_food_detail(self, tmp_detail_food):
        pdfs = list(tmp_detail_food.glob("*.pdf"))
        assert len(pdfs) > 0, "No food detail PDFs found"

        invoice = parse_food_detail(pdfs[0])
        assert invoice is not None
        assert len(invoice.order_id) == 15
        assert invoice.order_id.isdigit()
        assert invoice.invoice_total > 0
        assert len(invoice.items) > 0

    def test_all_food_details_total(self, tmp_detail_food):
        """Sum of food detail invoice_totals should be close to summary total.

        Known ~₹1,464 gap exists due to delivery fees not captured in detail PDFs.
        """
        pdfs = list(tmp_detail_food.glob("*.pdf"))
        total = 0.0
        parsed = 0

        for pdf in pdfs:
            invoice = parse_food_detail(pdf)
            if invoice and invoice.invoice_total > 0:
                total += invoice.invoice_total
                parsed += 1

        assert parsed == 36, f"Expected 36 food detail PDFs, got {parsed}"
        # Total should be roughly ₹44,633 - ₹1,464 = ~₹43,169
        assert total > 40000, f"Total {total} seems too low"


@pytest.mark.integration
class TestInstamartDetail:
    def test_parse_single_instamart_detail(self, tmp_detail_instamart):
        pdfs = list(tmp_detail_instamart.glob("*.pdf"))
        assert len(pdfs) > 0, "No instamart detail PDFs found"

        invoice = parse_instamart_detail(pdfs[0])
        assert invoice is not None
        assert len(invoice.order_id) == 15
        assert invoice.order_id.isdigit()
        assert len(invoice.items) > 0

    def test_all_instamart_details_total(self, tmp_detail_instamart):
        """Sum of instamart invoice_values should match summary total exactly."""
        pdfs = list(tmp_detail_instamart.glob("*.pdf"))
        total = 0.0
        parsed = 0

        for pdf in pdfs:
            invoice = parse_instamart_detail(pdf)
            if invoice and invoice.invoice_value > 0:
                total += invoice.invoice_value
                parsed += 1

        assert parsed == 55, f"Expected 55 instamart detail PDFs, got {parsed}"
        # Should match ₹57,779.44 exactly (within rounding)
        assert abs(total - 57779.44) < 1.0, f"Total {total} != expected 57779.44"

    def test_handling_fee_present(self, tmp_detail_instamart):
        """At least some instamart invoices should have handling fees."""
        pdfs = list(tmp_detail_instamart.glob("*.pdf"))
        has_handling = 0

        for pdf in pdfs:
            invoice = parse_instamart_detail(pdf)
            if invoice and invoice.handling_fee:
                has_handling += 1

        assert has_handling > 0, "No instamart invoices have handling fees"
