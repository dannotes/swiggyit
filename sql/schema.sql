-- SwiggyIt Database Schema
-- Auto-executed on first PostgreSQL container startup via docker-entrypoint-initdb.d

-- ============================================================
-- CUSTOMERS
-- ============================================================

CREATE TABLE IF NOT EXISTS customers (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    gstin           TEXT,
    address         TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- FOOD ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS food_orders (
    order_id            BIGINT PRIMARY KEY,
    customer_id         INT NOT NULL REFERENCES customers(id),

    -- Invoice metadata
    invoice_no          TEXT NOT NULL,
    document_type       TEXT NOT NULL DEFAULT 'INV',
    date_of_invoice     DATE NOT NULL,
    hsn_code            TEXT,
    service_description TEXT,
    category            TEXT,
    reverse_charges     BOOLEAN DEFAULT FALSE,

    -- Restaurant info
    restaurant_name     TEXT NOT NULL,
    restaurant_gstin    TEXT,
    restaurant_fssai    TEXT,
    restaurant_address  TEXT,
    restaurant_state    TEXT,

    -- Location
    place_of_supply     TEXT,

    -- Financials
    subtotal            NUMERIC(10,2) NOT NULL,
    igst_rate           NUMERIC(5,2) DEFAULT 0,
    igst_amount         NUMERIC(10,2) DEFAULT 0,
    cgst_rate           NUMERIC(5,2) DEFAULT 0,
    cgst_amount         NUMERIC(10,2) DEFAULT 0,
    sgst_rate           NUMERIC(5,2) DEFAULT 0,
    sgst_amount         NUMERIC(10,2) DEFAULT 0,
    total_taxes         NUMERIC(10,2) DEFAULT 0,
    invoice_total       NUMERIC(10,2) NOT NULL,

    -- ECO (E-Commerce Operator) details
    eco_name            TEXT,
    eco_gstin           TEXT,
    eco_fssai           TEXT,
    eco_address         TEXT,

    -- Source tracking
    detail_pdf_url      TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS food_order_items (
    id                   SERIAL PRIMARY KEY,
    order_id             BIGINT NOT NULL REFERENCES food_orders(order_id) ON DELETE CASCADE,

    sr_no                INT NOT NULL,
    description          TEXT NOT NULL,
    unit_of_measure      TEXT,
    quantity             INT NOT NULL,
    unit_price           NUMERIC(10,2) NOT NULL,
    amount               NUMERIC(10,2) NOT NULL,
    discount             NUMERIC(10,2) DEFAULT 0,
    net_assessable_value NUMERIC(10,2) NOT NULL,

    UNIQUE(order_id, sr_no)
);

-- ============================================================
-- INSTAMART ORDERS
-- ============================================================

CREATE TABLE IF NOT EXISTS instamart_orders (
    order_id            BIGINT PRIMARY KEY,
    customer_id         INT NOT NULL REFERENCES customers(id),

    -- Invoice metadata
    invoice_no          TEXT NOT NULL,
    document_type       TEXT NOT NULL DEFAULT 'INV',
    date_of_invoice     DATE NOT NULL,
    category            TEXT,

    -- Seller info
    seller_name         TEXT NOT NULL,
    seller_gstin        TEXT,
    seller_fssai        TEXT,
    seller_address      TEXT,
    seller_city         TEXT,
    seller_state        TEXT,

    -- Location
    place_of_supply     TEXT,

    -- Financials
    invoice_value       NUMERIC(10,2) NOT NULL,

    -- Source tracking
    detail_pdf_url      TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS instamart_order_items (
    id                  SERIAL PRIMARY KEY,
    order_id            BIGINT NOT NULL REFERENCES instamart_orders(order_id) ON DELETE CASCADE,

    sr_no               INT NOT NULL,
    description         TEXT NOT NULL,
    quantity            INT NOT NULL,
    uqc                 TEXT,
    hsn_sac_code        TEXT,

    -- Pricing
    taxable_value       NUMERIC(10,2) NOT NULL,
    discount            NUMERIC(10,2) DEFAULT 0,
    net_taxable_value   NUMERIC(10,2) NOT NULL,

    -- Per-item tax breakdown
    cgst_rate           NUMERIC(5,2) DEFAULT 0,
    cgst_amount         NUMERIC(10,2) DEFAULT 0,
    sgst_rate           NUMERIC(5,2) DEFAULT 0,
    sgst_amount         NUMERIC(10,2) DEFAULT 0,
    cess_rate           NUMERIC(5,2) DEFAULT 0,
    cess_amount         NUMERIC(10,2) DEFAULT 0,
    additional_cess     NUMERIC(10,2) DEFAULT 0,

    total_amount        NUMERIC(10,2) NOT NULL,

    UNIQUE(order_id, sr_no)
);

CREATE TABLE IF NOT EXISTS instamart_handling_fees (
    id                   SERIAL PRIMARY KEY,
    order_id             BIGINT NOT NULL REFERENCES instamart_orders(order_id) ON DELETE CASCADE,

    -- Invoice metadata
    invoice_no           TEXT NOT NULL,
    date_of_invoice      DATE NOT NULL,
    hsn_code             TEXT,
    hsn_description      TEXT,
    category             TEXT,
    transaction_type     TEXT,
    invoice_type         TEXT,
    reverse_charges      BOOLEAN DEFAULT FALSE,

    -- Swiggy (Invoice From)
    swiggy_pan           TEXT,
    swiggy_gstin         TEXT,
    swiggy_address       TEXT,
    swiggy_pincode       TEXT,
    swiggy_state_code    TEXT,

    -- Fee details
    description          TEXT,
    unit_price           NUMERIC(10,2) NOT NULL,
    discount             NUMERIC(10,2) DEFAULT 0,
    net_assessable_value NUMERIC(10,2) NOT NULL,

    -- Tax breakdown
    cgst_rate            NUMERIC(5,2) DEFAULT 0,
    cgst_amount          NUMERIC(10,2) DEFAULT 0,
    sgst_rate            NUMERIC(5,2) DEFAULT 0,
    sgst_amount          NUMERIC(10,2) DEFAULT 0,
    state_cess_rate      NUMERIC(5,2) DEFAULT 0,
    state_cess_amount    NUMERIC(10,2) DEFAULT 0,
    total_taxes          NUMERIC(10,2) DEFAULT 0,
    invoice_total        NUMERIC(10,2) NOT NULL,

    UNIQUE(order_id)
);

-- ============================================================
-- INDEXES
-- ============================================================

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
