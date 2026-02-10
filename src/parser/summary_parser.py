"""Parse Swiggy summary PDFs to extract customer info, order rows, and View URLs."""

import re
from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class OrderRow:
    date: str  # DD-MM-YYYY
    order_id: str
    name: str  # restaurant_name (food) or pod_name (instamart)
    amount: float
    detail_url: str


@dataclass
class SummaryData:
    order_type: str  # "food" or "instamart"
    customer_name: str
    customer_email: str
    number_of_orders: int
    total_amount: float
    date_range: str
    orders: list[OrderRow] = field(default_factory=list)


def _parse_amount(text: str) -> float:
    """Parse '₹1,774.50' or '₹1774.50' to float."""
    cleaned = text.replace("₹", "").replace(",", "").strip()
    return float(cleaned)


def _detect_order_type(file_path: Path) -> str:
    """Detect if the PDF is food or instamart from filename."""
    name = file_path.name.lower()
    if "food" in name:
        return "food"
    elif "instamart" in name:
        return "instamart"
    raise ValueError(f"Cannot detect order type from filename: {file_path.name}")


def _extract_header(lines: list[str]) -> dict:
    """Extract customer info from first page lines.

    Format (each field on its own line):
        Customer Name
        Number of Orders
        Total Amount
        John Doe
        36
        ₹44633.43
        Email
        Date Range
        john@example.com
        09-08-2025 to 09-02-2026
    """
    header = {}
    for i, line in enumerate(lines):
        # Labels appear as: "Customer Name" / "Number of Orders" / "Total Amount"
        # Values follow as:  "Dan Ny" / "36" / "₹44633.43"
        if line.strip() == "Customer Name" and i + 5 < len(lines):
            header["customer_name"] = lines[i + 3].strip()
            header["number_of_orders"] = int(lines[i + 4].strip())
            header["total_amount"] = _parse_amount(lines[i + 5].strip())
        # Labels: "Email" / "Date Range"
        # Values: "email@..." / "DD-MM-YYYY to DD-MM-YYYY"
        elif line.strip() == "Email" and i + 3 < len(lines):
            header["customer_email"] = lines[i + 2].strip()
            header["date_range"] = lines[i + 3].strip()
    return header


def _extract_urls(doc: fitz.Document) -> list[str]:
    """Extract all hyperlink URLs from the PDF."""
    urls = []
    for page in doc:
        for link in page.get_links():
            if "uri" in link:
                urls.append(link["uri"])
    return urls


DATE_PATTERN = re.compile(r"^\d{2}-\d{2}-\d{4}$")
ORDER_ID_PATTERN = re.compile(r"^\d{15}$")
AMOUNT_PATTERN = re.compile(r"^₹[\d,.]+$")


def _extract_order_rows(doc: fitz.Document) -> list[dict]:
    """Extract order rows by parsing lines sequentially.

    Each order appears as consecutive lines:
        DD-MM-YYYY          (date)
        123456789012345     (15-digit order_id)
        Restaurant Name     (name, may span multiple lines)
        ...                 (continued name lines)
        ₹1774.50            (amount)
        View                (link marker)
    """
    rows = []

    for page in doc:
        lines = page.get_text().split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for a date line as start of a row
            if DATE_PATTERN.match(line):
                date = line
                i += 1

                # Next should be order_id
                if i < len(lines) and ORDER_ID_PATTERN.match(lines[i].strip()):
                    order_id = lines[i].strip()
                    i += 1

                    # Collect name lines until we hit ₹amount
                    name_parts = []
                    while i < len(lines):
                        candidate = lines[i].strip()
                        if AMOUNT_PATTERN.match(candidate):
                            amount = _parse_amount(candidate)
                            i += 1
                            # Skip "View" line
                            if i < len(lines) and lines[i].strip() == "View":
                                i += 1
                            rows.append({
                                "date": date,
                                "order_id": order_id,
                                "name": " ".join(name_parts),
                                "amount": amount,
                            })
                            break
                        else:
                            name_parts.append(candidate)
                            i += 1
                else:
                    i += 1
            else:
                i += 1

    return rows


def parse_summary(file_path: Path) -> SummaryData:
    """Parse a Swiggy summary PDF and return structured data."""
    file_path = Path(file_path)
    order_type = _detect_order_type(file_path)
    doc = fitz.open(str(file_path))

    try:
        # Extract header from first page
        first_page_lines = doc[0].get_text().split("\n")
        header = _extract_header(first_page_lines)

        # Extract all View URLs
        urls = _extract_urls(doc)

        # Extract order rows from text
        rows = _extract_order_rows(doc)

        if len(urls) != len(rows):
            print(
                f"  Warning: {len(urls)} URLs but {len(rows)} rows "
                f"in {file_path.name}"
            )

        orders = []
        for i, row in enumerate(rows):
            url = urls[i] if i < len(urls) else ""
            orders.append(OrderRow(
                date=row["date"],
                order_id=row["order_id"],
                name=row["name"],
                amount=row["amount"],
                detail_url=url,
            ))

        return SummaryData(
            order_type=order_type,
            customer_name=header.get("customer_name", ""),
            customer_email=header.get("customer_email", ""),
            number_of_orders=header.get("number_of_orders", 0),
            total_amount=header.get("total_amount", 0.0),
            date_range=header.get("date_range", ""),
            orders=orders,
        )
    finally:
        doc.close()
