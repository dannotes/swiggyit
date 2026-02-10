"""Tests for src/loader.py."""

from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from validator import ValidationError, validate_date


class TestValidateDate:
    """Test date parsing via the validator (replaces old _parse_date)."""

    def test_valid(self):
        assert validate_date("15-01-2025") == "2025-01-15"

    def test_another_valid(self):
        assert validate_date("09-08-2025") == "2025-08-09"

    def test_invalid_raises(self):
        with pytest.raises(ValidationError):
            validate_date("2025-01-15")

    def test_empty_raises(self):
        with pytest.raises(ValidationError):
            validate_date("")


class TestUpsertFoodOrder:
    def _make_food_inv(self):
        return SimpleNamespace(
            order_id="123456789012345",
            invoice_no="INV-001",
            date_of_invoice="15-01-2025",
            document_type="INV",
            hsn_code="996331",
            service_description="Restaurant Service",
            category="B2C",
            reverse_charges=False,
            customer_name="Test",
            customer_gstin="URP",
            customer_address="123 Main St",
            restaurant_name="Test Kitchen",
            restaurant_gstin="29AABCT1234Z1",
            restaurant_fssai="11234567890123",
            restaurant_address="Plot 1",
            restaurant_state="Karnataka",
            place_of_supply="Karnataka",
            subtotal=500.0,
            igst_rate=0.0, igst_amount=0.0,
            cgst_rate=2.5, cgst_amount=12.5,
            sgst_rate=2.5, sgst_amount=12.5,
            total_taxes=25.0,
            invoice_total=525.0,
            eco_name="Bundl Tech",
            eco_gstin="29AABCB1234Z1",
            eco_fssai="11223344",
            eco_address="IBC Park",
            items=[
                SimpleNamespace(
                    sr_no=1, description="Biryani", unit_of_measure="Nos",
                    quantity=1, unit_price=500.0, amount=500.0,
                    discount=0.0, net_assessable_value=500.0,
                ),
            ],
        )

    def test_upsert_calls_sql(self):
        from loader import upsert_food_order

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        inv = self._make_food_inv()
        upsert_food_order(mock_conn, inv, 1, "https://example.com/pdf")

        # Should call execute 3 times: insert order, delete items, insert item
        assert mock_cursor.execute.call_count == 3

    def test_delete_before_insert_items(self):
        from loader import upsert_food_order

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        inv = self._make_food_inv()
        upsert_food_order(mock_conn, inv, 1, "https://example.com/pdf")

        # Second call should be DELETE
        second_call_sql = mock_cursor.execute.call_args_list[1][0][0]
        assert "DELETE FROM food_order_items" in second_call_sql


class TestUpsertInstamartOrder:
    def _make_instamart_inv(self):
        return SimpleNamespace(
            order_id="220939704984728",
            invoice_no="INM-001",
            date_of_invoice="15-01-2025",
            document_type="INV",
            category="B2C",
            customer_name="Test",
            customer_gstin="URP",
            customer_address="123 Main St",
            seller_name="Fresh Farms",
            seller_gstin="29AABCT1234Z1",
            seller_fssai="11234567890123",
            seller_address="Plot 5",
            seller_city="Bangalore",
            seller_state="Karnataka",
            place_of_supply="Karnataka",
            invoice_value=800.0,
            items=[
                SimpleNamespace(
                    sr_no=1, description="Milk", quantity=2, uqc="LTR",
                    hsn_sac_code="04012000", taxable_value=100.0,
                    discount=10.0, net_taxable_value=90.0,
                    cgst_rate=2.5, cgst_amount=2.25,
                    sgst_rate=2.5, sgst_amount=2.25,
                    cess_rate=0.0, cess_amount=0.0,
                    additional_cess=0.0, total_amount=94.50,
                ),
            ],
            handling_fee=None,
        )

    def test_upsert_calls_sql(self):
        from loader import upsert_instamart_order

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        inv = self._make_instamart_inv()
        upsert_instamart_order(mock_conn, inv, 1, "https://example.com/pdf")

        # insert order, delete items, insert item = 3 calls (no handling fee)
        assert mock_cursor.execute.call_count == 3

    def test_with_handling_fee(self):
        from loader import upsert_instamart_order

        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)

        inv = self._make_instamart_inv()
        inv.handling_fee = SimpleNamespace(
            invoice_no="HF-001",
            date_of_invoice="15-01-2025",
            hsn_code="996812",
            hsn_description="Handling",
            category="B2C",
            transaction_type="Regular",
            invoice_type="Regular",
            reverse_charges=False,
            swiggy_pan="AABCB1234A",
            swiggy_gstin="29AABCB1234Z1",
            swiggy_address="IBC Park",
            swiggy_pincode="560029",
            swiggy_state_code="29",
            description="Handling Fees",
            unit_price=50.0,
            discount=0.0,
            net_assessable_value=50.0,
            cgst_rate=9.0, cgst_amount=4.5,
            sgst_rate=9.0, sgst_amount=4.5,
            state_cess_rate=0.0, state_cess_amount=0.0,
            total_taxes=9.0,
            invoice_total=59.0,
        )

        upsert_instamart_order(mock_conn, inv, 1, "https://example.com/pdf")

        # insert order + delete items + insert item + insert handling = 4
        assert mock_cursor.execute.call_count == 4
