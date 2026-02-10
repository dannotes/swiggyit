"""SwiggyIt CLI - Parse Swiggy/Instamart PDFs and load into PostgreSQL."""

import argparse
import os
import sys
from pathlib import Path

import psycopg

from downloader import download_detail_pdfs
from loader import upsert_customer, upsert_food_order, upsert_instamart_order
from parser.food_parser import parse_food_detail
from parser.instamart_parser import parse_instamart_detail
from parser.summary_parser import parse_summary
from validator import (
    ValidationError,
    validate_email,
    validate_invoice_fields,
    validate_pdf_file,
    validate_summary_counts,
    validate_summary_folder,
)


def get_db_url() -> str:
    """Build PostgreSQL connection URL from environment or defaults."""
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "swiggyit")
    user = os.environ.get("POSTGRES_USER", "swiggyit")
    password = os.environ.get("POSTGRES_PASSWORD", "swiggyit_secret")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def process_food(input_dir: Path, tmp_dir: Path, conn):
    """Process all food summary PDFs."""
    food_dir = input_dir / "food"
    pdfs = list(food_dir.glob("order_summary_food_*.pdf"))
    if not pdfs:
        print("No food summary PDFs found in input/food/")
        return

    for pdf_path in pdfs:
        print(f"\n[Food] Parsing summary: {pdf_path.name}")

        try:
            validate_pdf_file(pdf_path)
        except ValidationError as e:
            print(f"  Skipping: {e}")
            continue

        summary = parse_summary(pdf_path)

        try:
            validate_summary_folder(pdf_path.parent.name, summary.order_type)
        except ValidationError as e:
            print(f"  Skipping: {e}")
            continue

        print(f"  Customer: {summary.customer_name} ({summary.customer_email})")
        print(f"  Orders: {summary.number_of_orders}")
        validate_email(summary.customer_email)
        validate_summary_counts(summary)

        # Upsert customer
        customer_id = upsert_customer(
            conn,
            summary.customer_name,
            summary.customer_email,
            "Unregistered",
            "",
        )
        conn.commit()

        # Download detail PDFs
        print("  Downloading detail PDFs...")
        detail_files = download_detail_pdfs(summary.orders, "food", tmp_dir)

        # Parse details and load
        loaded = 0
        failed = 0
        for order in summary.orders:
            detail_path = detail_files.get(order.order_id)
            if not detail_path:
                failed += 1
                continue

            try:
                validate_pdf_file(detail_path)
            except ValidationError as e:
                print(f"  Skipping order {order.order_id}: {e}")
                failed += 1
                continue

            invoice = parse_food_detail(detail_path)
            if not invoice or not invoice.order_id:
                failed += 1
                continue

            validate_invoice_fields(invoice, "food")

            try:
                upsert_food_order(conn, invoice, customer_id, order.detail_url)
                loaded += 1
            except ValidationError as e:
                print(f"  Skipping order {order.order_id}: {e}")
                failed += 1

        conn.commit()
        print(f"  Loaded: {loaded}/{len(summary.orders)} orders ({failed} failed)")


def process_instamart(input_dir: Path, tmp_dir: Path, conn):
    """Process all instamart summary PDFs."""
    instamart_dir = input_dir / "instamart"
    pdfs = list(instamart_dir.glob("order_summary_instamart_*.pdf"))
    if not pdfs:
        print("No instamart summary PDFs found in input/instamart/")
        return

    for pdf_path in pdfs:
        print(f"\n[Instamart] Parsing summary: {pdf_path.name}")

        try:
            validate_pdf_file(pdf_path)
        except ValidationError as e:
            print(f"  Skipping: {e}")
            continue

        summary = parse_summary(pdf_path)

        try:
            validate_summary_folder(pdf_path.parent.name, summary.order_type)
        except ValidationError as e:
            print(f"  Skipping: {e}")
            continue

        print(f"  Customer: {summary.customer_name} ({summary.customer_email})")
        print(f"  Orders: {summary.number_of_orders}")
        validate_email(summary.customer_email)
        validate_summary_counts(summary)

        # Upsert customer
        customer_id = upsert_customer(
            conn,
            summary.customer_name,
            summary.customer_email,
            "Unregistered",
            "",
        )
        conn.commit()

        # Download detail PDFs
        print("  Downloading detail PDFs...")
        detail_files = download_detail_pdfs(summary.orders, "instamart", tmp_dir)

        # Parse details and load
        loaded = 0
        failed = 0
        for order in summary.orders:
            detail_path = detail_files.get(order.order_id)
            if not detail_path:
                failed += 1
                continue

            try:
                validate_pdf_file(detail_path)
            except ValidationError as e:
                print(f"  Skipping order {order.order_id}: {e}")
                failed += 1
                continue

            invoice = parse_instamart_detail(detail_path)
            if not invoice or not invoice.order_id:
                failed += 1
                continue

            validate_invoice_fields(invoice, "instamart")

            try:
                upsert_instamart_order(conn, invoice, customer_id, order.detail_url)
                loaded += 1
            except ValidationError as e:
                print(f"  Skipping order {order.order_id}: {e}")
                failed += 1

        conn.commit()
        print(f"  Loaded: {loaded}/{len(summary.orders)} orders ({failed} failed)")


def main():
    parser = argparse.ArgumentParser(description="SwiggyIt - Swiggy bill parser and loader")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("input"),
        help="Input directory containing food/ and instamart/ folders (default: input)",
    )
    parser.add_argument(
        "--tmp",
        type=Path,
        default=Path(".tmp"),
        help="Temp directory for downloaded detail PDFs (default: .tmp)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="PostgreSQL connection URL (default: built from env vars)",
    )
    args = parser.parse_args()

    db_url = args.db_url or get_db_url()

    print("SwiggyIt - Swiggy Bill Parser")
    print("=" * 40)
    print(f"Input dir: {args.input.resolve()}")
    print(f"Temp dir:  {args.tmp.resolve()}")

    try:
        conn = psycopg.connect(db_url, autocommit=False)
    except psycopg.OperationalError as e:
        print(f"\nFailed to connect to PostgreSQL: {e}")
        print("Make sure the database is running: docker compose up -d postgres")
        sys.exit(1)

    print(f"Database:  connected")

    # Ensure schema exists (idempotent - safe to run every time)
    schema_path = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    if schema_path.exists():
        conn.execute(schema_path.read_text())
        conn.commit()

    try:
        process_food(args.input, args.tmp, conn)
        process_instamart(args.input, args.tmp, conn)
        print("\nDone!")
    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
