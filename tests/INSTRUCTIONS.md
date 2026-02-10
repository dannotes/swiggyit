# Running Tests

## Prerequisites

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Unit Tests (no Docker, no PDFs needed)

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py
```

These test all parser functions, validation logic, loader SQL calls, and downloader behavior using mocks. No database or PDF files required.

## Integration Tests (requires PDFs)

```bash
python -m pytest tests/ -v -m integration
```

These parse actual PDF files from `input/` and `.tmp/` directories. They verify:
- Food summary parses 36 orders
- Instamart summary parses 55 orders
- Detail PDFs have valid order IDs, items, and totals
- Instamart totals match expected ₹57,779.44
- Handling fees are present

Skipped automatically if the PDF directories don't exist.

## All Tests

```bash
python -m pytest tests/ -v
```

## With Coverage Report

```bash
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

## Test Structure

| File | What it tests | Type |
|------|--------------|------|
| `test_validator.py` | PDF validation, order ID, date, email, invoice field checks | Unit |
| `test_summary_parser.py` | Amount parsing, order type detection, header extraction, regex patterns | Unit |
| `test_food_parser.py` | Float parsing, header/tax/ECO block extraction | Unit |
| `test_instamart_parser.py` | Float parsing, seller/handling header and tax extraction | Unit |
| `test_loader.py` | Date validation, SQL upsert calls with mocked DB | Unit |
| `test_downloader.py` | Cache hits, missing URLs, HTTP downloads/errors with mocked httpx | Unit |
| `test_integration.py` | End-to-end parsing of actual PDFs, total verification | Integration |
