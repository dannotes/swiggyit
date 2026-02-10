"""Parse Swiggy food detail invoice PDFs using pdfplumber."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber


@dataclass
class FoodItem:
    sr_no: int
    description: str
    unit_of_measure: str
    quantity: int
    unit_price: float
    amount: float
    discount: float
    net_assessable_value: float


@dataclass
class FoodInvoice:
    # Invoice metadata
    order_id: str
    invoice_no: str
    date_of_invoice: str
    document_type: str
    hsn_code: str
    service_description: str
    category: str
    reverse_charges: bool

    # Customer info
    customer_name: str
    customer_gstin: str
    customer_address: str

    # Restaurant info
    restaurant_name: str
    restaurant_gstin: str
    restaurant_fssai: str
    restaurant_address: str
    restaurant_state: str

    # Location
    place_of_supply: str

    # Financials
    subtotal: float
    igst_rate: float
    igst_amount: float
    cgst_rate: float
    cgst_amount: float
    sgst_rate: float
    sgst_amount: float
    total_taxes: float
    invoice_total: float

    # ECO details
    eco_name: str
    eco_gstin: str
    eco_fssai: str
    eco_address: str

    # Items
    items: list[FoodItem] = field(default_factory=list)


def _parse_float(val: str) -> float:
    """Safely parse a float from string."""
    if not val:
        return 0.0
    cleaned = val.replace(",", "").replace("₹", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_header(header_text: str) -> dict:
    """Parse the merged header cell with two-column layout.

    Uses specific patterns per field to avoid two-column bleed.
    """
    data = {}
    t = header_text

    # Left column fields (stop before right-column labels)
    m = re.search(r"Invoice To:\s*(.+?)(?:\s{2,}Invoice issued)", t)
    data["customer_name"] = m.group(1).strip() if m else ""

    m = re.search(r"^GSTIN:\s*(\S+)", t, re.MULTILINE)
    data["customer_gstin"] = m.group(1).strip() if m else ""

    m = re.search(r"Customer Address:\s*(.+?)(?:\s{2,}Restaurant GSTIN)", t)
    data["customer_address"] = m.group(1).strip() if m else ""

    m = re.search(r"Order ID:\s*(\d+)", t)
    data["order_id"] = m.group(1).strip() if m else ""

    m = re.search(r"Document:\s*(\S+)", t)
    data["document_type"] = m.group(1).strip() if m else "INV"

    m = re.search(r"Invoice No:\s*(\S+)", t)
    data["invoice_no"] = m.group(1).strip() if m else ""

    m = re.search(r"Date of Invoice:\s*(\d{2}-\d{2}-\d{4})", t)
    data["date_of_invoice"] = m.group(1).strip() if m else ""

    m = re.search(r"HSN Code:\s*(\d+)", t)
    data["hsn_code"] = m.group(1).strip() if m else ""

    # Right column fields
    m = re.search(r"Restaurant Name:\s*(.+?)$", t, re.MULTILINE)
    data["restaurant_name"] = m.group(1).strip() if m else ""

    m = re.search(r"Restaurant GSTIN:\s*(\S+)", t)
    data["restaurant_gstin"] = m.group(1).strip() if m else ""

    m = re.search(r"Restaurant FSSAI License:\s*(\S+)", t)
    data["restaurant_fssai"] = m.group(1).strip() if m else ""

    m = re.search(
        r"Restaurant FSSAI License:.*?\nAddress:\s*(.+?)(?=\nState:)",
        t,
        re.DOTALL,
    )
    data["restaurant_address"] = " ".join(m.group(1).split()) if m else ""

    m = re.search(r"^State:\s*(.+?)$", t, re.MULTILINE)
    data["restaurant_state"] = m.group(1).strip() if m else ""

    m = re.search(r"Place of Supply:\s*(.+?)$", t, re.MULTILINE)
    data["place_of_supply"] = m.group(1).strip() if m else ""

    m = re.search(r"Service Description:\s*(.+?)$", t, re.MULTILINE)
    data["service_description"] = m.group(1).strip() if m else ""

    m = re.search(r"Category:\s*(\S+)", t)
    data["category"] = m.group(1).strip() if m else ""

    m = re.search(r"Reverse Charges Applicable:\s*(\S+)", t)
    data["reverse_charges"] = m.group(1).strip() if m else "No"

    return data


def _parse_tax_block(tax_text: str) -> dict:
    """Parse the tax summary block."""
    taxes = {
        "igst_rate": 0.0, "igst_amount": 0.0,
        "cgst_rate": 0.0, "cgst_amount": 0.0,
        "sgst_rate": 0.0, "sgst_amount": 0.0,
        "total_taxes": 0.0, "invoice_total": 0.0,
    }

    igst = re.search(r"IGST\s+([\d.]+)%\s+([\d,.]+)", tax_text)
    if igst:
        taxes["igst_rate"] = float(igst.group(1))
        taxes["igst_amount"] = _parse_float(igst.group(2))

    cgst = re.search(r"CGST\s+([\d.]+)%\s+([\d,.]+)", tax_text)
    if cgst:
        taxes["cgst_rate"] = float(cgst.group(1))
        taxes["cgst_amount"] = _parse_float(cgst.group(2))

    sgst = re.search(r"SGST/UTGST\s+([\d.]+)%\s+([\d,.]+)", tax_text)
    if sgst:
        taxes["sgst_rate"] = float(sgst.group(1))
        taxes["sgst_amount"] = _parse_float(sgst.group(2))

    total = re.search(r"Total taxes\s+([\d,.]+)", tax_text)
    if total:
        taxes["total_taxes"] = _parse_float(total.group(1))

    inv_total = re.search(r"Invoice Total\s+([\d,.]+)", tax_text)
    if inv_total:
        taxes["invoice_total"] = _parse_float(inv_total.group(1))

    return taxes


def _parse_eco_block(eco_text: str) -> dict:
    """Parse the ECO details block."""
    eco = {"eco_name": "", "eco_gstin": "", "eco_fssai": "", "eco_address": ""}

    name = re.search(r"Name:\s*(.+?)(?:\n|$)", eco_text)
    if name:
        eco["eco_name"] = name.group(1).strip()

    addr = re.search(r"Address:\s*(.+?)(?:\n|$)", eco_text)
    if addr:
        eco["eco_address"] = addr.group(1).strip()

    gstin = re.search(r"GSTIN:\s*(\S+)", eco_text)
    if gstin:
        eco["eco_gstin"] = gstin.group(1).strip()

    fssai = re.search(r"Swiggy FSSAI:\s*(\S+)", eco_text)
    if fssai:
        eco["eco_fssai"] = fssai.group(1).strip()

    return eco


def parse_food_detail(file_path: Path) -> FoodInvoice | None:
    """Parse a food detail invoice PDF and return structured data."""
    try:
        pdf = pdfplumber.open(str(file_path))
    except Exception as e:
        print(f"  Failed to open {file_path.name}: {e}")
        return None

    try:
        page = pdf.pages[0]
        tables = page.extract_tables()

        if not tables or len(tables[0]) < 8:
            print(f"  Unexpected table structure in {file_path.name}")
            return None

        table = tables[0]

        # Row 2: merged header cell
        header_text = table[2][0] or ""
        header = _parse_header(header_text)

        # Rows 3+: items header then item rows until "Subtotal"
        items = []
        subtotal = 0.0
        for row in table[4:]:  # skip header row at index 3
            if row[1] and row[1].strip() == "Subtotal":
                # Subtotal value is always in the last cell
                subtotal = _parse_float(row[-1])
                break
            if row[0] and "Subtotal" in row[0]:
                subtotal = _parse_float(row[-1])
                break
            if row[0] and row[0].strip().rstrip(".").isdigit():
                # Some PDFs have 9 cols (with None spacer), some have 8
                if len(row) >= 9:
                    uom, qty = row[2], row[3]
                    price, amt, disc, nav = row[5], row[6], row[7], row[8]
                else:
                    uom, qty = row[2], row[3]
                    price, amt, disc, nav = row[4], row[5], row[6], row[7]
                items.append(FoodItem(
                    sr_no=int(row[0].strip().rstrip(".")),
                    description=row[1].strip() if row[1] else "",
                    unit_of_measure=uom.strip() if uom else "",
                    quantity=int(qty.strip()) if qty else 0,
                    unit_price=_parse_float(price),
                    amount=_parse_float(amt),
                    discount=_parse_float(disc),
                    net_assessable_value=_parse_float(nav),
                ))

        # Tax block
        tax_row = next(
            (r for r in table if r[0] and "Taxes" in r[0] and "CGST" in r[0]),
            None,
        )
        taxes = _parse_tax_block(tax_row[0]) if tax_row else {}

        # ECO block
        eco_row = next(
            (r for r in table if r[0] and "ECO under GST" in r[0]),
            None,
        )
        eco = _parse_eco_block(eco_row[0]) if eco_row else {}

        return FoodInvoice(
            order_id=header.get("order_id", ""),
            invoice_no=header.get("invoice_no", ""),
            date_of_invoice=header.get("date_of_invoice", ""),
            document_type=header.get("document_type", "INV"),
            hsn_code=header.get("hsn_code", ""),
            service_description=header.get("service_description", ""),
            category=header.get("category", ""),
            reverse_charges=header.get("reverse_charges", "").lower() == "yes",
            customer_name=header.get("customer_name", ""),
            customer_gstin=header.get("customer_gstin", ""),
            customer_address=header.get("customer_address", ""),
            restaurant_name=header.get("restaurant_name", ""),
            restaurant_gstin=header.get("restaurant_gstin", ""),
            restaurant_fssai=header.get("restaurant_fssai", ""),
            restaurant_address=header.get("restaurant_address", ""),
            restaurant_state=header.get("restaurant_state", ""),
            place_of_supply=header.get("place_of_supply", ""),
            subtotal=subtotal,
            igst_rate=taxes.get("igst_rate", 0.0),
            igst_amount=taxes.get("igst_amount", 0.0),
            cgst_rate=taxes.get("cgst_rate", 0.0),
            cgst_amount=taxes.get("cgst_amount", 0.0),
            sgst_rate=taxes.get("sgst_rate", 0.0),
            sgst_amount=taxes.get("sgst_amount", 0.0),
            total_taxes=taxes.get("total_taxes", 0.0),
            invoice_total=taxes.get("invoice_total", 0.0),
            eco_name=eco.get("eco_name", ""),
            eco_gstin=eco.get("eco_gstin", ""),
            eco_fssai=eco.get("eco_fssai", ""),
            eco_address=eco.get("eco_address", ""),
            items=items,
        )
    finally:
        pdf.close()
