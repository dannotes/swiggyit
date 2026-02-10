"""Upsert parsed invoice data into PostgreSQL."""

import psycopg

from validator import validate_date, validate_order_id


def upsert_customer(conn, name: str, email: str, gstin: str, address: str) -> int:
    """Upsert a customer and return the customer_id."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO customers (name, email, gstin, address)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET
                name = EXCLUDED.name,
                address = EXCLUDED.address
            RETURNING id
            """,
            (name, email, gstin, address),
        )
        return cur.fetchone()[0]


def upsert_food_order(conn, inv, customer_id: int, detail_url: str):
    """Upsert a food order and its items."""
    validate_order_id(inv.order_id, "food order")
    order_id = int(inv.order_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO food_orders (
                order_id, customer_id, invoice_no, document_type,
                date_of_invoice, hsn_code, service_description, category,
                reverse_charges, restaurant_name, restaurant_gstin,
                restaurant_fssai, restaurant_address, restaurant_state,
                place_of_supply, subtotal, igst_rate, igst_amount,
                cgst_rate, cgst_amount, sgst_rate, sgst_amount,
                total_taxes, invoice_total, eco_name, eco_gstin,
                eco_fssai, eco_address, detail_pdf_url
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (order_id) DO UPDATE SET
                customer_id = EXCLUDED.customer_id,
                invoice_no = EXCLUDED.invoice_no,
                document_type = EXCLUDED.document_type,
                date_of_invoice = EXCLUDED.date_of_invoice,
                hsn_code = EXCLUDED.hsn_code,
                service_description = EXCLUDED.service_description,
                category = EXCLUDED.category,
                reverse_charges = EXCLUDED.reverse_charges,
                restaurant_name = EXCLUDED.restaurant_name,
                restaurant_gstin = EXCLUDED.restaurant_gstin,
                restaurant_fssai = EXCLUDED.restaurant_fssai,
                restaurant_address = EXCLUDED.restaurant_address,
                restaurant_state = EXCLUDED.restaurant_state,
                place_of_supply = EXCLUDED.place_of_supply,
                subtotal = EXCLUDED.subtotal,
                igst_rate = EXCLUDED.igst_rate,
                igst_amount = EXCLUDED.igst_amount,
                cgst_rate = EXCLUDED.cgst_rate,
                cgst_amount = EXCLUDED.cgst_amount,
                sgst_rate = EXCLUDED.sgst_rate,
                sgst_amount = EXCLUDED.sgst_amount,
                total_taxes = EXCLUDED.total_taxes,
                invoice_total = EXCLUDED.invoice_total,
                eco_name = EXCLUDED.eco_name,
                eco_gstin = EXCLUDED.eco_gstin,
                eco_fssai = EXCLUDED.eco_fssai,
                eco_address = EXCLUDED.eco_address,
                detail_pdf_url = EXCLUDED.detail_pdf_url,
                updated_at = NOW()
            """,
            (
                order_id, customer_id, inv.invoice_no, inv.document_type,
                validate_date(inv.date_of_invoice, "food order"), inv.hsn_code,
                inv.service_description, inv.category, inv.reverse_charges,
                inv.restaurant_name, inv.restaurant_gstin, inv.restaurant_fssai,
                inv.restaurant_address, inv.restaurant_state, inv.place_of_supply,
                inv.subtotal, inv.igst_rate, inv.igst_amount,
                inv.cgst_rate, inv.cgst_amount, inv.sgst_rate, inv.sgst_amount,
                inv.total_taxes, inv.invoice_total,
                inv.eco_name, inv.eco_gstin, inv.eco_fssai, inv.eco_address,
                detail_url,
            ),
        )

        # Delete + reinsert items
        cur.execute("DELETE FROM food_order_items WHERE order_id = %s", (order_id,))
        for item in inv.items:
            cur.execute(
                """
                INSERT INTO food_order_items (
                    order_id, sr_no, description, unit_of_measure,
                    quantity, unit_price, amount, discount, net_assessable_value
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    order_id, item.sr_no, item.description, item.unit_of_measure,
                    item.quantity, item.unit_price, item.amount,
                    item.discount, item.net_assessable_value,
                ),
            )


def upsert_instamart_order(conn, inv, customer_id: int, detail_url: str):
    """Upsert an instamart order, its items, and handling fee."""
    validate_order_id(inv.order_id, "instamart order")
    order_id = int(inv.order_id)

    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO instamart_orders (
                order_id, customer_id, invoice_no, document_type,
                date_of_invoice, category, seller_name, seller_gstin,
                seller_fssai, seller_address, seller_city, seller_state,
                place_of_supply, invoice_value, detail_pdf_url
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (order_id) DO UPDATE SET
                customer_id = EXCLUDED.customer_id,
                invoice_no = EXCLUDED.invoice_no,
                document_type = EXCLUDED.document_type,
                date_of_invoice = EXCLUDED.date_of_invoice,
                category = EXCLUDED.category,
                seller_name = EXCLUDED.seller_name,
                seller_gstin = EXCLUDED.seller_gstin,
                seller_fssai = EXCLUDED.seller_fssai,
                seller_address = EXCLUDED.seller_address,
                seller_city = EXCLUDED.seller_city,
                seller_state = EXCLUDED.seller_state,
                place_of_supply = EXCLUDED.place_of_supply,
                invoice_value = EXCLUDED.invoice_value,
                detail_pdf_url = EXCLUDED.detail_pdf_url,
                updated_at = NOW()
            """,
            (
                order_id, customer_id, inv.invoice_no, inv.document_type,
                validate_date(inv.date_of_invoice, "instamart order"), inv.category,
                inv.seller_name, inv.seller_gstin, inv.seller_fssai,
                inv.seller_address, inv.seller_city, inv.seller_state,
                inv.place_of_supply, inv.invoice_value, detail_url,
            ),
        )

        # Delete + reinsert items
        cur.execute(
            "DELETE FROM instamart_order_items WHERE order_id = %s", (order_id,)
        )
        for item in inv.items:
            cur.execute(
                """
                INSERT INTO instamart_order_items (
                    order_id, sr_no, description, quantity, uqc,
                    hsn_sac_code, taxable_value, discount, net_taxable_value,
                    cgst_rate, cgst_amount, sgst_rate, sgst_amount,
                    cess_rate, cess_amount, additional_cess, total_amount
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    order_id, item.sr_no, item.description, item.quantity,
                    item.uqc, item.hsn_sac_code, item.taxable_value,
                    item.discount, item.net_taxable_value,
                    item.cgst_rate, item.cgst_amount,
                    item.sgst_rate, item.sgst_amount,
                    item.cess_rate, item.cess_amount,
                    item.additional_cess, item.total_amount,
                ),
            )

        # Upsert handling fee
        if inv.handling_fee:
            hf = inv.handling_fee
            cur.execute(
                """
                INSERT INTO instamart_handling_fees (
                    order_id, invoice_no, date_of_invoice, hsn_code,
                    hsn_description, category, transaction_type, invoice_type,
                    reverse_charges, swiggy_pan, swiggy_gstin, swiggy_address,
                    swiggy_pincode, swiggy_state_code, description, unit_price,
                    discount, net_assessable_value, cgst_rate, cgst_amount,
                    sgst_rate, sgst_amount, state_cess_rate, state_cess_amount,
                    total_taxes, invoice_total
                ) VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s
                )
                ON CONFLICT (order_id) DO UPDATE SET
                    invoice_no = EXCLUDED.invoice_no,
                    date_of_invoice = EXCLUDED.date_of_invoice,
                    hsn_code = EXCLUDED.hsn_code,
                    hsn_description = EXCLUDED.hsn_description,
                    category = EXCLUDED.category,
                    transaction_type = EXCLUDED.transaction_type,
                    invoice_type = EXCLUDED.invoice_type,
                    reverse_charges = EXCLUDED.reverse_charges,
                    swiggy_pan = EXCLUDED.swiggy_pan,
                    swiggy_gstin = EXCLUDED.swiggy_gstin,
                    swiggy_address = EXCLUDED.swiggy_address,
                    swiggy_pincode = EXCLUDED.swiggy_pincode,
                    swiggy_state_code = EXCLUDED.swiggy_state_code,
                    description = EXCLUDED.description,
                    unit_price = EXCLUDED.unit_price,
                    discount = EXCLUDED.discount,
                    net_assessable_value = EXCLUDED.net_assessable_value,
                    cgst_rate = EXCLUDED.cgst_rate,
                    cgst_amount = EXCLUDED.cgst_amount,
                    sgst_rate = EXCLUDED.sgst_rate,
                    sgst_amount = EXCLUDED.sgst_amount,
                    state_cess_rate = EXCLUDED.state_cess_rate,
                    state_cess_amount = EXCLUDED.state_cess_amount,
                    total_taxes = EXCLUDED.total_taxes,
                    invoice_total = EXCLUDED.invoice_total
                """,
                (
                    order_id, hf.invoice_no, validate_date(hf.date_of_invoice, "handling fee"),
                    hf.hsn_code, hf.hsn_description, hf.category,
                    hf.transaction_type, hf.invoice_type, hf.reverse_charges,
                    hf.swiggy_pan, hf.swiggy_gstin, hf.swiggy_address,
                    hf.swiggy_pincode, hf.swiggy_state_code,
                    hf.description, hf.unit_price, hf.discount,
                    hf.net_assessable_value, hf.cgst_rate, hf.cgst_amount,
                    hf.sgst_rate, hf.sgst_amount, hf.state_cess_rate,
                    hf.state_cess_amount, hf.total_taxes, hf.invoice_total,
                ),
            )
