"""Validation functions for SwiggyIt pipeline."""

import re
from datetime import datetime
from pathlib import Path


class ValidationError(Exception):
    """Raised for validation errors that should skip a record."""
    pass


def validate_pdf_file(path: Path) -> None:
    """Validate that a file exists, is non-empty, and starts with PDF magic bytes."""
    if not path.exists():
        raise ValidationError(f"File not found: {path}")
    if path.stat().st_size == 0:
        raise ValidationError(f"Empty file: {path}")
    with open(path, "rb") as f:
        magic = f.read(5)
    if magic != b"%PDF-":
        raise ValidationError(f"Not a valid PDF (bad magic bytes): {path.name}")


def validate_summary_folder(folder_name: str, detected_type: str) -> None:
    """Cross-check that the folder name matches the detected order type."""
    folder_lower = folder_name.lower()
    if detected_type == "food" and "instamart" in folder_lower:
        raise ValidationError(
            f"Folder mismatch: file detected as 'food' but in '{folder_name}/' folder"
        )
    if detected_type == "instamart" and "food" in folder_lower:
        raise ValidationError(
            f"Folder mismatch: file detected as 'instamart' but in '{folder_name}/' folder"
        )


def validate_order_id(order_id: str, context: str = "") -> None:
    """Validate order_id is a 15-digit numeric string."""
    if not order_id:
        raise ValidationError(f"Empty order_id{' in ' + context if context else ''}")
    if not re.match(r"^\d{15}$", order_id):
        raise ValidationError(
            f"Invalid order_id '{order_id}' (expected 15 digits)"
            f"{' in ' + context if context else ''}"
        )


def validate_date(date_str: str, context: str = "") -> str:
    """Validate and convert DD-MM-YYYY to YYYY-MM-DD for PostgreSQL.

    Raises ValidationError instead of silently returning bad data.
    """
    if not date_str:
        raise ValidationError(f"Empty date{' in ' + context if context else ''}")
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        raise ValidationError(
            f"Invalid date format '{date_str}' (expected DD-MM-YYYY)"
            f"{' in ' + context if context else ''}"
        )


_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email(email: str) -> bool:
    """Validate email format. Returns False and prints warning if invalid."""
    if not email:
        print("  Warning: Empty customer email")
        return False
    if not _EMAIL_RE.match(email):
        print(f"  Warning: Suspicious email format: {email}")
        return False
    return True


def validate_invoice_fields(inv, order_type: str) -> bool:
    """Warn about suspicious invoice field values. Returns True if all OK."""
    ok = True

    if not inv.order_id:
        print(f"  Warning: [{order_type}] Missing order_id")
        ok = False

    if not inv.date_of_invoice:
        print(f"  Warning: [{order_type}] Missing date_of_invoice for order {inv.order_id}")
        ok = False

    if not inv.invoice_no:
        print(f"  Warning: [{order_type}] Missing invoice_no for order {inv.order_id}")
        ok = False

    if order_type == "food":
        if not inv.restaurant_name:
            print(f"  Warning: [food] Missing restaurant_name for order {inv.order_id}")
            ok = False
        if inv.invoice_total <= 0:
            print(f"  Warning: [food] Zero/negative invoice_total for order {inv.order_id}")
            ok = False
        if not inv.items:
            print(f"  Warning: [food] No items parsed for order {inv.order_id}")
            ok = False

    elif order_type == "instamart":
        if not inv.seller_name:
            print(f"  Warning: [instamart] Missing seller_name for order {inv.order_id}")
            ok = False
        if inv.invoice_value <= 0:
            print(f"  Warning: [instamart] Zero/negative invoice_value for order {inv.order_id}")
            ok = False
        if not inv.items:
            print(f"  Warning: [instamart] No items parsed for order {inv.order_id}")
            ok = False

    return ok


def validate_summary_counts(summary) -> bool:
    """Warn if parsed order count doesn't match header count. Returns True if OK."""
    actual = len(summary.orders)
    expected = summary.number_of_orders
    if actual != expected:
        print(
            f"  Warning: Summary header says {expected} orders "
            f"but parsed {actual} order rows"
        )
        return False
    return True
