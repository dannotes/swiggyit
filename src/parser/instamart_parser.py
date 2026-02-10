"""Parse Swiggy Instamart detail invoice PDFs using pdfplumber.

Each PDF contains 2 invoices:
  Page 1: Seller/product invoice with per-item tax breakdown
  Page 2: Swiggy handling fee invoice
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber


@dataclass
class InstamartItem:
    sr_no: int
    description: str
    quantity: int
    uqc: str
    hsn_sac_code: str
    taxable_value: float
    discount: float
    net_taxable_value: float
    cgst_rate: float
    cgst_amount: float
    sgst_rate: float
    sgst_amount: float
    cess_rate: float
    cess_amount: float
    additional_cess: float
    total_amount: float


@dataclass
class HandlingFee:
    invoice_no: str
    date_of_invoice: str
    hsn_code: str
    hsn_description: str
    category: str
    transaction_type: str
    invoice_type: str
    reverse_charges: bool
    swiggy_pan: str
    swiggy_gstin: str
    swiggy_address: str
    swiggy_pincode: str
    swiggy_state_code: str
    description: str
    unit_price: float
    discount: float
    net_assessable_value: float
    cgst_rate: float
    cgst_amount: float
    sgst_rate: float
    sgst_amount: float
    state_cess_rate: float
    state_cess_amount: float
    total_taxes: float
    invoice_total: float


@dataclass
class InstamartInvoice:
    # Invoice metadata
    order_id: str
    invoice_no: str
    date_of_invoice: str
    document_type: str
    category: str

    # Customer info
    customer_name: str
    customer_gstin: str
    customer_address: str

    # Seller info
    seller_name: str
    seller_gstin: str
    seller_fssai: str
    seller_address: str
    seller_city: str
    seller_state: str

    # Location
    place_of_supply: str

    # Financials
    invoice_value: float

    # Items
    items: list[InstamartItem] = field(default_factory=list)

    # Handling fee (page 2)
    handling_fee: HandlingFee | None = None


def _pf(val: str) -> float:
    """Parse float from string."""
    if not val:
        return 0.0
    cleaned = val.replace(",", "").replace("₹", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_seller_header(text: str) -> dict:
    """Parse page 1 header (seller invoice metadata)."""
    d = {}

    m = re.search(r"Invoice To:\s*(.+?)(?:\s{2,}Seller Name)", text)
    d["customer_name"] = m.group(1).strip() if m else ""

    m = re.search(r"^GSTIN:\s*(\S+)", text, re.MULTILINE)
    d["customer_gstin"] = m.group(1).strip() if m else ""

    m = re.search(r"Customer Address:\s*(.+?)(?:\s{2,}FSSAI)", text)
    d["customer_address"] = m.group(1).strip() if m else ""

    m = re.search(r"Order ID:\s*(\d+)", text)
    d["order_id"] = m.group(1).strip() if m else ""

    m = re.search(r"Document:\s*(\S+)", text)
    d["document_type"] = m.group(1).strip() if m else "INV"

    m = re.search(r"Invoice No:\s*(\S+)", text)
    d["invoice_no"] = m.group(1).strip() if m else ""

    m = re.search(r"Date of Invoice:\s*(\d{2}-\d{2}-\d{4})", text)
    d["date_of_invoice"] = m.group(1).strip() if m else ""

    m = re.search(r"Category:\s*(\S+)", text)
    d["category"] = m.group(1).strip() if m else ""

    # Right column
    m = re.search(r"Seller Name:\s*(.+?)$", text, re.MULTILINE)
    d["seller_name"] = m.group(1).strip() if m else ""

    m = re.search(r"Seller GSTIN:\s*(\S+)", text)
    d["seller_gstin"] = m.group(1).strip() if m else ""

    m = re.search(r"FSSAI:\s*(\S+)", text)
    d["seller_fssai"] = m.group(1).strip() if m else ""

    # Seller address: after "Address:" on right side (after Order ID line)
    m = re.search(r"Order ID:.*?\nAddress:\s*(.+?)(?=\nDocument:)", text, re.DOTALL)
    if not m:
        m = re.search(r"Address:\s*(.+?)(?=\nCity:|\nDocument:)", text, re.DOTALL)
    d["seller_address"] = " ".join(m.group(1).split()) if m else ""

    m = re.search(r"City:\s*(.+?)$", text, re.MULTILINE)
    d["seller_city"] = m.group(1).strip() if m else ""

    m = re.search(r"State:\s*(.+?)$", text, re.MULTILINE)
    d["seller_state"] = m.group(1).strip() if m else ""

    m = re.search(r"Place of Supply:\s*(.+?)$", text, re.MULTILINE)
    d["place_of_supply"] = m.group(1).strip() if m else ""

    return d


def _parse_handling_header(text: str) -> dict:
    """Parse page 2 header (handling fee invoice metadata)."""
    d = {}

    m = re.search(r"PAN:\s*(\S+)", text)
    d["swiggy_pan"] = m.group(1).strip() if m else ""

    m = re.search(r"^GSTIN:\s*(\S+)", text, re.MULTILINE)
    d["swiggy_gstin"] = m.group(1).strip() if m else ""

    # Swiggy address: after their GSTIN line
    m = re.search(r"GSTIN:.*?\nAddress:\s*(.+?)(?=\nPincode:)", text, re.DOTALL)
    d["swiggy_address"] = " ".join(m.group(1).split()) if m else ""

    m = re.search(r"Pincode:\s*(\S+)", text)
    d["swiggy_pincode"] = m.group(1).strip() if m else ""

    m = re.search(r"State Code:\s*(\S+)", text)
    d["swiggy_state_code"] = m.group(1).strip() if m else ""

    m = re.search(r"Invoice No:\s*(\S+)", text)
    d["invoice_no"] = m.group(1).strip() if m else ""

    m = re.search(r"Date of Invoice:\s*(\d{2}-\d{2}-\d{4})", text)
    d["date_of_invoice"] = m.group(1).strip() if m else ""

    m = re.search(r"Category:\s*(\S+)", text)
    d["category"] = m.group(1).strip() if m else ""

    m = re.search(r"Transaction Type:\s*(\S+)", text)
    d["transaction_type"] = m.group(1).strip() if m else ""

    m = re.search(r"Invoice Type:\s*(\S+)", text)
    d["invoice_type"] = m.group(1).strip() if m else ""

    m = re.search(r"Whether Reverse Charges\s*(\S+)", text)
    d["reverse_charges"] = m.group(1).strip() if m else "No"

    return d


def _parse_handling_tax(tax_text: str) -> dict:
    """Parse tax block from page 2 handling fee invoice."""
    taxes = {}

    m = re.search(r"CGST\s+([\d.]+)%\s+([\d,.]+)", tax_text)
    if m:
        taxes["cgst_rate"] = float(m.group(1))
        taxes["cgst_amount"] = _pf(m.group(2))

    m = re.search(r"SGST/UTGST\s+([\d.]+)%\s+([\d,.]+)", tax_text)
    if m:
        taxes["sgst_rate"] = float(m.group(1))
        taxes["sgst_amount"] = _pf(m.group(2))

    m = re.search(r"State CESS\s+([\d.]+)%\s+([\d,.]+)", tax_text)
    if m:
        taxes["state_cess_rate"] = float(m.group(1))
        taxes["state_cess_amount"] = _pf(m.group(2))

    m = re.search(r"Total taxes\s+([\d,.]+)", tax_text)
    taxes["total_taxes"] = _pf(m.group(1)) if m else 0.0

    m = re.search(r"Invoice Total\s+([\d,.]+)", tax_text)
    taxes["invoice_total"] = _pf(m.group(1)) if m else 0.0

    # HSN info
    m = re.search(r"(\d{6})\s+(.+?)(?:\n|Total taxes)", tax_text)
    if m:
        taxes["hsn_code"] = m.group(1).strip()
        taxes["hsn_description"] = m.group(2).strip()

    return taxes


def parse_instamart_detail(file_path: Path) -> InstamartInvoice | None:
    """Parse an instamart detail invoice PDF and return structured data."""
    try:
        pdf = pdfplumber.open(str(file_path))
    except Exception as e:
        print(f"  Failed to open {file_path.name}: {e}")
        return None

    try:
        # ---- PAGE 1: Seller / Product Invoice ----
        page1 = pdf.pages[0]
        table1 = page1.extract_tables()[0]

        # Row 1: merged header
        header = _parse_seller_header(table1[1][0] or "")

        # Rows 3+: item rows (row 2 is column headers)
        items = []
        invoice_value = 0.0
        for row in table1[3:]:
            if row[0] and "Invoice Value" in row[0]:
                invoice_value = _pf(row[-1])
                continue
            if row[0] and "Amount in words" in row[0]:
                continue
            if row[0] and row[0].strip().rstrip(".").isdigit():
                items.append(InstamartItem(
                    sr_no=int(row[0].strip().rstrip(".")),
                    description=" ".join((row[1] or "").split()),
                    quantity=int(row[2].strip()) if row[2] else 0,
                    uqc=(row[3] or "").strip(),
                    hsn_sac_code=(row[4] or "").strip(),
                    taxable_value=_pf(row[5]),
                    discount=_pf(row[6]),
                    net_taxable_value=_pf(row[7]),
                    cgst_rate=_pf(row[8]),
                    cgst_amount=_pf(row[9]),
                    sgst_rate=_pf(row[10]),
                    sgst_amount=_pf(row[11]),
                    cess_rate=_pf(row[12]),
                    cess_amount=_pf(row[13]),
                    additional_cess=_pf(row[14]),
                    total_amount=_pf(row[15]),
                ))

        # ---- PAGE 2: Handling Fee Invoice ----
        inv_order_id = header.get("order_id", "")
        handling = None
        if len(pdf.pages) >= 2:
            page2 = pdf.pages[1]
            table2 = page2.extract_tables()[0]

            # Row 2: merged header
            h_header = _parse_handling_header(table2[2][0] or "")

            # Row 4: handling fee item
            h_item_row = None
            for row in table2[3:]:
                if row[0] and row[0].strip().rstrip(".").isdigit():
                    h_item_row = row
                    break

            # Tax block
            h_tax_row = next(
                (r for r in table2 if r[0] and "Taxes" in r[0] and "CGST" in r[0]),
                None,
            )
            h_taxes = _parse_handling_tax(h_tax_row[0]) if h_tax_row else {}

            # Build handling fee — may have a line item or be zero-fee
            if h_item_row:
                h_desc = " ".join((h_item_row[1] or "").split())
                # Column layout varies (9 or 10 cols)
                if len(h_item_row) >= 10:
                    h_unit_price = _pf(h_item_row[5])
                    h_discount = _pf(h_item_row[8])
                    h_nav = _pf(h_item_row[9])
                else:
                    h_unit_price = _pf(h_item_row[5])
                    h_discount = _pf(h_item_row[7])
                    h_nav = _pf(h_item_row[8])
            else:
                # Zero-fee invoice (no item row)
                h_desc = f"Handling Fees for Order {inv_order_id}"
                h_unit_price = 0.0
                h_discount = 0.0
                h_nav = 0.0

            handling = HandlingFee(
                invoice_no=h_header.get("invoice_no", ""),
                date_of_invoice=h_header.get("date_of_invoice", ""),
                hsn_code=h_taxes.get("hsn_code", ""),
                hsn_description=h_taxes.get("hsn_description", ""),
                category=h_header.get("category", ""),
                transaction_type=h_header.get("transaction_type", ""),
                invoice_type=h_header.get("invoice_type", ""),
                reverse_charges=h_header.get("reverse_charges", "No").lower() == "yes",
                swiggy_pan=h_header.get("swiggy_pan", ""),
                swiggy_gstin=h_header.get("swiggy_gstin", ""),
                swiggy_address=h_header.get("swiggy_address", ""),
                swiggy_pincode=h_header.get("swiggy_pincode", ""),
                swiggy_state_code=h_header.get("swiggy_state_code", ""),
                description=h_desc,
                unit_price=h_unit_price,
                discount=h_discount,
                net_assessable_value=h_nav,
                cgst_rate=h_taxes.get("cgst_rate", 0.0),
                cgst_amount=h_taxes.get("cgst_amount", 0.0),
                sgst_rate=h_taxes.get("sgst_rate", 0.0),
                sgst_amount=h_taxes.get("sgst_amount", 0.0),
                state_cess_rate=h_taxes.get("state_cess_rate", 0.0),
                state_cess_amount=h_taxes.get("state_cess_amount", 0.0),
                total_taxes=h_taxes.get("total_taxes", 0.0),
                invoice_total=h_taxes.get("invoice_total", 0.0),
            )

        return InstamartInvoice(
            order_id=header.get("order_id", ""),
            invoice_no=header.get("invoice_no", ""),
            date_of_invoice=header.get("date_of_invoice", ""),
            document_type=header.get("document_type", "INV"),
            category=header.get("category", ""),
            customer_name=header.get("customer_name", ""),
            customer_gstin=header.get("customer_gstin", ""),
            customer_address=header.get("customer_address", ""),
            seller_name=header.get("seller_name", ""),
            seller_gstin=header.get("seller_gstin", ""),
            seller_fssai=header.get("seller_fssai", ""),
            seller_address=header.get("seller_address", ""),
            seller_city=header.get("seller_city", ""),
            seller_state=header.get("seller_state", ""),
            place_of_supply=header.get("place_of_supply", ""),
            invoice_value=invoice_value,
            items=items,
            handling_fee=handling,
        )
    finally:
        pdf.close()
