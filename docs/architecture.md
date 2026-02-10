# SwiggyIt - Architecture Document

## 1. Project Overview

SwiggyIt is a personal finance tool that extracts order data from Swiggy Food and Swiggy Instamart PDF bills, stores it in PostgreSQL, and enables querying/analysis via Grafana dashboards.

### Goals
- Parse Swiggy summary PDFs (food + instamart) to extract order lists and detail PDF URLs
- Fetch and parse each detailed invoice PDF for item-level data
- Store everything in PostgreSQL with full upsert support (idempotent re-runs)
- Support multiple customers (e.g., family members) from separate PDF exports
- Visualize spending patterns via Grafana

---

## 2. Data Sources

### 2.1 Summary PDFs (exported from Swiggy account)

Two types of summary PDFs are exported from Swiggy:

| File | Type | Example |
|------|------|---------|
| `order_summary_food_<uuid>.pdf` | Swiggy Food | 36 orders, 2 pages |
| `order_summary_instamart_<uuid>.pdf` | Swiggy Instamart | 55 orders, 4 pages |

**Summary PDF Header Fields:**
- Customer Name, Email, Number of Orders, Total Amount, Date Range

**Summary PDF Row Fields (per order):**

| Field | Food | Instamart |
|-------|------|-----------|
| Date / Time | yes | yes |
| Order ID | yes | yes |
| Restaurant Name | yes | - |
| Pod Name (Seller) | - | yes |
| Amount | yes | yes |
| View (hyperlink to detail PDF) | yes | yes |

### 2.2 Detail PDFs (fetched via "View" hyperlinks)

Each "View" link in the summary PDF points to a pre-signed S3 URL:
- Food: `https://internal-payments.s3.amazonaws.com/taco/<id>_<uuid>.pdf`
- Instamart: `https://internal-payments.s3.amazonaws.com/taco/<order_id>_merged.pdf`

**Note:** These S3 URLs have an `Expires` parameter and are time-limited. All detail PDFs should be downloaded promptly after exporting the summary.

---

## 3. Detail PDF Structure

### 3.1 Food Detail Invoice (1 page, 1 invoice per order)

```
TAX INVOICE
├── Invoice Header
│   ├── Customer: name, GSTIN, address
│   ├── Restaurant: name, GSTIN, FSSAI, address, state
│   ├── Order ID, Invoice No, Date, HSN Code (996331)
│   ├── Document type (INV), Category (B2C)
│   ├── Place of Supply, Service Description (Restaurant Service)
│   └── Reverse Charges Applicable (No)
├── Line Items Table
│   ├── Sr No
│   ├── Description (item name)
│   ├── Unit of Measure (OTH)
│   ├── Quantity
│   ├── Unit Price
│   ├── Amount (Rs.)
│   ├── Discount
│   └── Net Assessable Value (Rs.)
├── Subtotal
├── Tax Summary (order-level)
│   ├── IGST: rate + amount
│   ├── CGST: rate + amount
│   ├── SGST/UTGST: rate + amount
│   └── Total Taxes
├── Invoice Total
└── ECO Details (Swiggy Limited: name, GSTIN, FSSAI, address)
```

### 3.2 Instamart Detail Invoice (2 pages, 2 invoices merged per order)

**Page 1 - Seller/Product Invoice:**
```
TAX INVOICE
├── Invoice Header
│   ├── Customer: name, GSTIN, address
│   ├── Seller: name, GSTIN, FSSAI, address, city, state
│   ├── Order ID, Invoice No, Date
│   ├── Place of Supply, Category (B2C)
├── Line Items Table (per-item tax breakdown!)
│   ├── Sr No
│   ├── Description of Goods
│   ├── Quantity
│   ├── UQC (unit - NOS, KGS, etc.)
│   ├── HSN/SAC Code (unique per item!)
│   ├── Taxable Value (base/MRP)
│   ├── Discount (Excluding Taxes)
│   ├── Net Taxable Value
│   ├── CGST %  +  CGST amount
│   ├── SGST %  +  SGST amount
│   ├── Cess %  +  Cess amount
│   ├── Additional Cess
│   └── Total Amount (Rs.)
└── Invoice Value (total)
```

**Page 2 - Swiggy Handling Fee Invoice:**
```
TAX INVOICE
├── Invoice From: Swiggy Limited (PAN, GSTIN, address, pincode, state code)
├── Invoice To: Customer (name, address)
├── Invoice No, Date, Category, Transaction Type (REG), Invoice Type (RG)
├── Reverse Charges Applicable (No)
├── Line Item
│   ├── Description: "Handling Fees for Order <order_id>"
│   ├── HSN: 999799 (Other Services)
│   ├── Unit Price, Discount, Net Assessable Value
├── Tax Summary
│   ├── CGST: rate + amount
│   ├── SGST/UTGST: rate + amount
│   ├── State CESS: rate + amount
│   └── Total Taxes
└── Invoice Total
```

### 3.3 Key Differences

| Aspect | Food | Instamart |
|--------|------|-----------|
| Invoices per order | 1 | 2 (product + handling fee) |
| Item HSN code | Same for all (996331) | Unique per item |
| Tax breakdown | Order-level only | Per-item CGST, SGST, Cess |
| Discount | Per-item (simple) | Per-item (excluding taxes) |
| Seller entity | Restaurant | Retail pod (warehouse) |
| Handling/platform fee | Baked into subtotal | Separate invoice |
| FSSAI | Restaurant + Swiggy | Seller + Swiggy |

---

## 4. Database

### 4.1 Choice: PostgreSQL

**Why PostgreSQL over SQLite:**
- Native Grafana datasource (no community plugins needed)
- Strong date/time functions for time-series dashboards
- `ON CONFLICT` upsert support for idempotent re-runs
- Better aggregation and window functions for analytics
- Scales if more data sources are added later

### 4.2 Schema (6 tables)

```
customers
  ├── food_orders              (customer_id FK, order_id PK)
  │     └── food_order_items   (order_id FK)
  │
  ├── instamart_orders         (customer_id FK, order_id PK)
  │     ├── instamart_order_items      (order_id FK)
  │     └── instamart_handling_fees    (order_id FK, 1:1)
```

### 4.3 Table Definitions

#### `customers`
| Column | Type | Constraints | Example |
|--------|------|-------------|---------|
| id | SERIAL | PK | 1 |
| name | TEXT | NOT NULL | John Doe |
| email | TEXT | UNIQUE, NOT NULL | john.doe@example.com |
| gstin | TEXT | | Unregistered |
| address | TEXT | | 123 Sample Street... |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |

#### `food_orders`
| Column | Type | Constraints | Example |
|--------|------|-------------|---------|
| order_id | BIGINT | PK | 100000000000001 |
| customer_id | INT | FK → customers(id), NOT NULL | 1 |
| invoice_no | TEXT | NOT NULL | 1000000000000001 |
| document_type | TEXT | DEFAULT 'INV' | INV |
| date_of_invoice | DATE | NOT NULL | 2025-08-09 |
| hsn_code | TEXT | | 996331 |
| service_description | TEXT | | Restaurant Service |
| category | TEXT | | B2C |
| reverse_charges | BOOLEAN | DEFAULT FALSE | false |
| restaurant_name | TEXT | NOT NULL | Sample Restaurant |
| restaurant_gstin | TEXT | | 32XXXXX0000X1ZX |
| restaurant_fssai | TEXT | | 10000000000001 |
| restaurant_address | TEXT | | 1/23, Some Street... |
| restaurant_state | TEXT | | Kerala |
| place_of_supply | TEXT | | Kerala |
| subtotal | NUMERIC(10,2) | NOT NULL | 1690.00 |
| igst_rate | NUMERIC(5,2) | DEFAULT 0 | 0 |
| igst_amount | NUMERIC(10,2) | DEFAULT 0 | 0.00 |
| cgst_rate | NUMERIC(5,2) | DEFAULT 0 | 2.5 |
| cgst_amount | NUMERIC(10,2) | DEFAULT 0 | 42.25 |
| sgst_rate | NUMERIC(5,2) | DEFAULT 0 | 2.5 |
| sgst_amount | NUMERIC(10,2) | DEFAULT 0 | 42.25 |
| total_taxes | NUMERIC(10,2) | DEFAULT 0 | 84.50 |
| invoice_total | NUMERIC(10,2) | NOT NULL | 1774.50 |
| eco_name | TEXT | | Swiggy Limited |
| eco_gstin | TEXT | | 32XXXXX0000X1Z3 |
| eco_fssai | TEXT | | 10000000000002 |
| eco_address | TEXT | | Some Address... |
| detail_pdf_url | TEXT | | S3 presigned URL |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | |

#### `food_order_items`
| Column | Type | Constraints | Example |
|--------|------|-------------|---------|
| id | SERIAL | PK | 1 |
| order_id | BIGINT | FK → food_orders(order_id), NOT NULL | 100000000000001 |
| sr_no | INT | NOT NULL | 1 |
| description | TEXT | NOT NULL | Chicken Biryani Full |
| unit_of_measure | TEXT | | OTH |
| quantity | INT | NOT NULL | 1 |
| unit_price | NUMERIC(10,2) | NOT NULL | 880.00 |
| amount | NUMERIC(10,2) | NOT NULL | 880.00 |
| discount | NUMERIC(10,2) | DEFAULT 0 | 0.00 |
| net_assessable_value | NUMERIC(10,2) | NOT NULL | 880.00 |
| | | UNIQUE(order_id, sr_no) | |

#### `instamart_orders`
| Column | Type | Constraints | Example |
|--------|------|-------------|---------|
| order_id | BIGINT | PK | 200000000000001 |
| customer_id | INT | FK → customers(id), NOT NULL | 1 |
| invoice_no | TEXT | NOT NULL | 250821IMXXX00001 |
| document_type | TEXT | DEFAULT 'INV' | INV |
| date_of_invoice | DATE | NOT NULL | 2025-08-21 |
| category | TEXT | | B2C |
| seller_name | TEXT | NOT NULL | Sample Retail Pvt Ltd - Location |
| seller_gstin | TEXT | | 32XXXXX0000X1ZP |
| seller_fssai | TEXT | | 20250000000000001 |
| seller_address | TEXT | | Ground Floor, Some Building... |
| seller_city | TEXT | | Kochi |
| seller_state | TEXT | | Kerala |
| place_of_supply | TEXT | | Kerala |
| invoice_value | NUMERIC(10,2) | NOT NULL | 1008.00 |
| detail_pdf_url | TEXT | | S3 presigned URL |
| created_at | TIMESTAMPTZ | DEFAULT NOW() | |
| updated_at | TIMESTAMPTZ | DEFAULT NOW() | |

#### `instamart_order_items`
| Column | Type | Constraints | Example |
|--------|------|-------------|---------|
| id | SERIAL | PK | 1 |
| order_id | BIGINT | FK → instamart_orders(order_id), NOT NULL | 200000000000001 |
| sr_no | INT | NOT NULL | 1 |
| description | TEXT | NOT NULL | Whole Wheat Pasta 500g |
| quantity | INT | NOT NULL | 1 |
| uqc | TEXT | | NOS |
| hsn_sac_code | TEXT | | 19021900 |
| taxable_value | NUMERIC(10,2) | NOT NULL | 156.25 |
| discount | NUMERIC(10,2) | DEFAULT 0 | 83.04 |
| net_taxable_value | NUMERIC(10,2) | NOT NULL | 73.21 |
| cgst_rate | NUMERIC(5,2) | DEFAULT 0 | 6 |
| cgst_amount | NUMERIC(10,2) | DEFAULT 0 | 4.39 |
| sgst_rate | NUMERIC(5,2) | DEFAULT 0 | 6 |
| sgst_amount | NUMERIC(10,2) | DEFAULT 0 | 4.39 |
| cess_rate | NUMERIC(5,2) | DEFAULT 0 | 0 |
| cess_amount | NUMERIC(10,2) | DEFAULT 0 | 0 |
| additional_cess | NUMERIC(10,2) | DEFAULT 0 | 0 |
| total_amount | NUMERIC(10,2) | NOT NULL | 82.00 |
| | | UNIQUE(order_id, sr_no) | |

#### `instamart_handling_fees`
| Column | Type | Constraints | Example |
|--------|------|-------------|---------|
| id | SERIAL | PK | 1 |
| order_id | BIGINT | FK → instamart_orders(order_id), UNIQUE | 200000000000001 |
| invoice_no | TEXT | NOT NULL | 250821SWXX000001 |
| date_of_invoice | DATE | NOT NULL | 2025-08-21 |
| hsn_code | TEXT | | 999799 |
| hsn_description | TEXT | | Other Services |
| category | TEXT | | B2C |
| transaction_type | TEXT | | REG |
| invoice_type | TEXT | | RG |
| reverse_charges | BOOLEAN | DEFAULT FALSE | false |
| swiggy_pan | TEXT | | XXXXX0000X |
| swiggy_gstin | TEXT | | 32XXXXX0000X1Z3 |
| swiggy_address | TEXT | | Some Address... |
| swiggy_pincode | TEXT | | 600001 |
| swiggy_state_code | TEXT | | 32 |
| description | TEXT | | Handling Fees for Order 200000000000001 |
| unit_price | NUMERIC(10,2) | NOT NULL | 14.90 |
| discount | NUMERIC(10,2) | DEFAULT 0 | 0 |
| net_assessable_value | NUMERIC(10,2) | NOT NULL | 14.90 |
| cgst_rate | NUMERIC(5,2) | DEFAULT 0 | 9 |
| cgst_amount | NUMERIC(10,2) | DEFAULT 0 | 1.34 |
| sgst_rate | NUMERIC(5,2) | DEFAULT 0 | 9 |
| sgst_amount | NUMERIC(10,2) | DEFAULT 0 | 1.34 |
| state_cess_rate | NUMERIC(5,2) | DEFAULT 0 | 0 |
| state_cess_amount | NUMERIC(10,2) | DEFAULT 0 | 0.00 |
| total_taxes | NUMERIC(10,2) | DEFAULT 0 | 2.68 |
| invoice_total | NUMERIC(10,2) | NOT NULL | 17.58 |

---

## 5. Upsert Strategy (Idempotent Re-runs)

Running the same PDFs multiple times must not create duplicates.

### Customers
```sql
INSERT INTO customers (name, email, gstin, address)
VALUES (...)
ON CONFLICT (email) DO UPDATE SET
    name = EXCLUDED.name,
    address = EXCLUDED.address;
-- Returns customer_id for use in order inserts
```

### Orders (food_orders, instamart_orders)
```sql
INSERT INTO food_orders (order_id, customer_id, ...)
VALUES (...)
ON CONFLICT (order_id) DO UPDATE SET
    invoice_no = EXCLUDED.invoice_no,
    ... (all columns),
    updated_at = NOW();
```

### Order Items (food_order_items, instamart_order_items)
Items use delete-and-reinsert within a transaction (simpler than per-row upserts):
```sql
BEGIN;
DELETE FROM food_order_items WHERE order_id = <order_id>;
INSERT INTO food_order_items (order_id, sr_no, ...) VALUES (...), (...);
COMMIT;
```

### Handling Fees (instamart_handling_fees)
```sql
INSERT INTO instamart_handling_fees (order_id, ...)
VALUES (...)
ON CONFLICT (order_id) DO UPDATE SET
    ... (all columns);
```

---

## 6. Data Pipeline

```
Downloads/
├── order_summary_food_<uuid>.pdf          ─┐
├── order_summary_instamart_<uuid>.pdf      │
                                            │
Step 1: Parse summary PDFs                  │
  - Extract customer info (header)          │
  - Extract order rows (date, id, name,     │
    amount)                                 │
  - Extract "View" hyperlink URLs           │
                                            ▼
Step 2: Download detail PDFs           detail_food_*.pdf
  - Fetch each S3 URL                 detail_instamart_*.pdf
  - Save locally for parsing
                                            │
Step 3: Parse detail PDFs                   │
  - Food: extract 1 invoice per PDF         │
  - Instamart: extract 2 invoices per PDF   │
    (seller invoice + handling fee)         │
                                            ▼
Step 4: Load into PostgreSQL
  - Upsert customer
  - Upsert orders
  - Delete + reinsert items
  - Upsert handling fees
                                            │
                                            ▼
Step 5: Grafana dashboards
  - Connect PostgreSQL as datasource
  - Build panels (see section 7)
```

### Tech Stack
- **Language:** Python 3.12+
- **PDF link extraction:** PyMuPDF (fitz) — extract "View" hyperlink URLs from summary PDFs
- **PDF table parsing:** pdfplumber — extract structured invoice tables from detail PDFs
- **Database driver:** psycopg 3 — modern PostgreSQL driver with native upsert support
- **HTTP client:** httpx — download detail PDFs from S3 pre-signed URLs
- **CLI:** argparse (stdlib) — zero extra dependencies
- **Dashboards:** Grafana with native PostgreSQL datasource

### CLI Design
Single command that runs the full pipeline:
```bash
python src/main.py --input ./input
```
Steps executed in order: parse summaries → download details → parse details → load into PostgreSQL

---

## 7. Grafana Dashboard Ideas

| Panel | Query Approach |
|-------|---------------|
| Monthly spend trend (food vs instamart) | `date_of_invoice` grouped by month, SUM of totals |
| Top restaurants (food) | GROUP BY `restaurant_name`, SUM `invoice_total` |
| Top sellers (instamart) | GROUP BY `seller_name`, SUM `invoice_value` |
| Most ordered food items | GROUP BY `food_order_items.description`, COUNT + SUM |
| Most bought grocery items | GROUP BY `instamart_order_items.description`, COUNT + SUM |
| Tax paid over time | SUM `total_taxes` by month |
| Discount savings (instamart) | SUM `instamart_order_items.discount` by month |
| Handling fees trend | SUM `instamart_handling_fees.invoice_total` by month |
| Average order value by day-of-week | AVG of totals grouped by EXTRACT(DOW) |
| HSN-wise spending (instamart) | GROUP BY `hsn_sac_code` |
| Orders per week heatmap | COUNT orders by week |
| Customer comparison | Split all panels by `customer_id` |

---

## 8. Indexes

```sql
-- Time-series queries (Grafana)
CREATE INDEX idx_food_orders_date ON food_orders(date_of_invoice);
CREATE INDEX idx_instamart_orders_date ON instamart_orders(date_of_invoice);

-- Grouping queries
CREATE INDEX idx_food_orders_restaurant ON food_orders(restaurant_name);
CREATE INDEX idx_instamart_orders_seller ON instamart_orders(seller_name);
CREATE INDEX idx_instamart_items_hsn ON instamart_order_items(hsn_sac_code);

-- FK lookups
CREATE INDEX idx_food_items_order ON food_order_items(order_id);
CREATE INDEX idx_instamart_items_order ON instamart_order_items(order_id);
CREATE INDEX idx_instamart_fees_order ON instamart_handling_fees(order_id);

-- Multi-customer filtering
CREATE INDEX idx_food_orders_customer ON food_orders(customer_id);
CREATE INDEX idx_instamart_orders_customer ON instamart_orders(customer_id);
```

---

## 9. Folder Structure

```
swiggyit/
├── input/                       # User drops exported PDFs here
│   ├── food/                    #   Swiggy food summary PDFs
│   └── instamart/               #   Instamart summary PDFs
├── .tmp/                        # Auto-created, gitignored. Processing cache
│   ├── detail_food/             #   Downloaded food detail PDFs
│   └── detail_instamart/        #   Downloaded instamart detail PDFs
├── docs/
│   └── architecture.md          # This file
├── deploy/
│   ├── docker-compose.yml       # PostgreSQL container
│   └── .env.example             # Environment variable template
├── sql/
│   └── schema.sql               # CREATE TABLE statements (auto-run on first start)
├── src/
│   ├── parser/
│   │   ├── summary_parser.py    # Parse summary PDFs, extract URLs (PyMuPDF)
│   │   ├── food_parser.py       # Parse food detail invoices (pdfplumber)
│   │   └── instamart_parser.py  # Parse instamart detail invoices (pdfplumber)
│   ├── downloader.py            # Fetch detail PDFs from S3 URLs (httpx)
│   ├── loader.py                # Upsert data into PostgreSQL (psycopg 3)
│   └── main.py                  # CLI entrypoint (argparse)
├── requirements.txt
├── .gitignore
└── README.md
```

### Folder Roles

| Folder | Managed by | Purpose |
|--------|-----------|---------|
| `input/` | User | Drop exported Swiggy PDFs here. Separated by type (food/instamart) |
| `.tmp/` | Application | Auto-created at runtime. Caches downloaded detail PDFs so S3 URL expiry doesn't matter after first run. Gitignored |
| `docs/` | Developer | Architecture and design docs |
| `deploy/` | Developer | Docker compose for infrastructure |
| `sql/` | Developer | Schema DDL, mounted into PostgreSQL container |
| `src/` | Developer | Application code |
