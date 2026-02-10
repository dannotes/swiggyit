-- ============================================================
-- SwiggyIt - Analysis Queries
-- Run any section independently against the swiggyit database
-- ============================================================


-- ============================================================
-- 1. OVERALL DASHBOARD
-- ============================================================

-- 1.1 Complete spending overview
SELECT
    'Food' AS type,
    count(*) AS orders,
    sum(invoice_total) AS total_spend,
    round(avg(invoice_total), 2) AS avg_order,
    min(invoice_total) AS min_order,
    max(invoice_total) AS max_order
FROM food_orders
UNION ALL
SELECT
    'Instamart',
    count(*),
    sum(invoice_value),
    round(avg(invoice_value), 2),
    min(invoice_value),
    max(invoice_value)
FROM instamart_orders;

-- 1.2 Grand total across all platforms
SELECT
    count(*) AS total_orders,
    sum(total) AS grand_total
FROM (
    SELECT invoice_total AS total FROM food_orders
    UNION ALL
    SELECT invoice_value FROM instamart_orders
) combined;

-- 1.3 Total items purchased
SELECT
    'Food Items' AS type, count(*) AS count, sum(quantity) AS total_qty
FROM food_order_items
UNION ALL
SELECT
    'Instamart Items', count(*), sum(quantity)
FROM instamart_order_items;


-- ============================================================
-- 2. MONTHLY SPENDING TRENDS
-- ============================================================

-- 2.1 Monthly breakdown: food vs instamart side by side
SELECT
    month,
    coalesce(food_orders, 0) AS food_orders,
    coalesce(food_spend, 0) AS food_spend,
    coalesce(instamart_orders, 0) AS instamart_orders,
    coalesce(instamart_spend, 0) AS instamart_spend,
    coalesce(food_spend, 0) + coalesce(instamart_spend, 0) AS total_spend
FROM (
    SELECT date_trunc('month', date_of_invoice)::date AS month,
           count(*) AS food_orders,
           round(sum(invoice_total), 2) AS food_spend
    FROM food_orders GROUP BY 1
) f
FULL OUTER JOIN (
    SELECT date_trunc('month', date_of_invoice)::date AS month,
           count(*) AS instamart_orders,
           round(sum(invoice_value), 2) AS instamart_spend
    FROM instamart_orders GROUP BY 1
) i USING (month)
ORDER BY month;

-- 2.2 Month-over-month growth rate
WITH monthly AS (
    SELECT
        date_trunc('month', date_of_invoice)::date AS month,
        sum(invoice_total) AS spend
    FROM food_orders
    GROUP BY 1
)
SELECT
    month,
    spend,
    lag(spend) OVER (ORDER BY month) AS prev_month,
    round(
        (spend - lag(spend) OVER (ORDER BY month))
        / NULLIF(lag(spend) OVER (ORDER BY month), 0) * 100, 1
    ) AS growth_pct
FROM monthly
ORDER BY month;

-- 2.3 Weekly spending trend
SELECT
    date_trunc('week', date_of_invoice)::date AS week_start,
    count(*) AS orders,
    round(sum(total), 2) AS spend
FROM (
    SELECT date_of_invoice, invoice_total AS total FROM food_orders
    UNION ALL
    SELECT date_of_invoice, invoice_value FROM instamart_orders
) all_orders
GROUP BY 1
ORDER BY 1;


-- ============================================================
-- 3. RESTAURANT ANALYSIS (FOOD)
-- ============================================================

-- 3.1 Top restaurants by total spend
SELECT
    restaurant_name,
    count(*) AS orders,
    round(sum(invoice_total), 2) AS total_spend,
    round(avg(invoice_total), 2) AS avg_order,
    min(date_of_invoice) AS first_order,
    max(date_of_invoice) AS last_order
FROM food_orders
GROUP BY restaurant_name
ORDER BY total_spend DESC;

-- 3.2 Top restaurants by order frequency
SELECT
    restaurant_name,
    count(*) AS order_count,
    round(sum(invoice_total), 2) AS total_spend,
    round(
        extract(epoch FROM max(date_of_invoice) - min(date_of_invoice)) / 86400.0
        / NULLIF(count(*) - 1, 0), 1
    ) AS avg_days_between_orders
FROM food_orders
GROUP BY restaurant_name
HAVING count(*) > 1
ORDER BY order_count DESC;

-- 3.3 Restaurant spending by month (pivot-style)
SELECT
    restaurant_name,
    count(*) FILTER (WHERE date_trunc('month', date_of_invoice) = '2025-08-01') AS aug_25,
    count(*) FILTER (WHERE date_trunc('month', date_of_invoice) = '2025-09-01') AS sep_25,
    count(*) FILTER (WHERE date_trunc('month', date_of_invoice) = '2025-10-01') AS oct_25,
    count(*) FILTER (WHERE date_trunc('month', date_of_invoice) = '2025-11-01') AS nov_25,
    count(*) FILTER (WHERE date_trunc('month', date_of_invoice) = '2025-12-01') AS dec_25,
    count(*) FILTER (WHERE date_trunc('month', date_of_invoice) = '2026-01-01') AS jan_26,
    count(*) FILTER (WHERE date_trunc('month', date_of_invoice) = '2026-02-01') AS feb_26
FROM food_orders
GROUP BY restaurant_name
ORDER BY count(*) DESC;


-- ============================================================
-- 4. SELLER ANALYSIS (INSTAMART)
-- ============================================================

-- 4.1 Top sellers by spend
SELECT
    seller_name,
    count(*) AS orders,
    round(sum(invoice_value), 2) AS total_spend,
    round(avg(invoice_value), 2) AS avg_order
FROM instamart_orders
GROUP BY seller_name
ORDER BY total_spend DESC;

-- 4.2 Seller order frequency over time
SELECT
    seller_name,
    date_trunc('month', date_of_invoice)::date AS month,
    count(*) AS orders,
    round(sum(invoice_value), 2) AS spend
FROM instamart_orders
GROUP BY 1, 2
ORDER BY 1, 2;


-- ============================================================
-- 5. FOOD ITEM ANALYSIS
-- ============================================================

-- 5.1 Most ordered food items (by quantity)
SELECT
    description,
    sum(quantity) AS total_qty,
    count(DISTINCT order_id) AS in_orders,
    round(avg(unit_price), 2) AS avg_unit_price,
    round(sum(net_assessable_value), 2) AS total_spend
FROM food_order_items
WHERE description NOT ILIKE '%packing%'
GROUP BY description
ORDER BY total_qty DESC
LIMIT 20;

-- 5.2 Most expensive food items ordered
SELECT
    description,
    quantity,
    unit_price,
    net_assessable_value,
    fo.restaurant_name,
    fo.date_of_invoice
FROM food_order_items fi
JOIN food_orders fo ON fi.order_id = fo.order_id
ORDER BY unit_price DESC
LIMIT 15;

-- 5.3 Food items by restaurant
SELECT
    fo.restaurant_name,
    fi.description,
    sum(fi.quantity) AS total_qty,
    round(avg(fi.unit_price), 2) AS avg_price
FROM food_order_items fi
JOIN food_orders fo ON fi.order_id = fo.order_id
WHERE fi.description NOT ILIKE '%packing%'
GROUP BY 1, 2
ORDER BY 1, total_qty DESC;

-- 5.4 Price changes for frequently ordered items
SELECT
    fi.description,
    fo.date_of_invoice,
    fi.unit_price,
    lag(fi.unit_price) OVER (PARTITION BY fi.description ORDER BY fo.date_of_invoice) AS prev_price,
    fi.unit_price - lag(fi.unit_price) OVER (PARTITION BY fi.description ORDER BY fo.date_of_invoice) AS price_change
FROM food_order_items fi
JOIN food_orders fo ON fi.order_id = fo.order_id
WHERE fi.description IN (
    SELECT description FROM food_order_items
    WHERE description NOT ILIKE '%packing%'
    GROUP BY description HAVING count(*) >= 3
)
ORDER BY fi.description, fo.date_of_invoice;


-- ============================================================
-- 6. INSTAMART ITEM ANALYSIS
-- ============================================================

-- 6.1 Most bought instamart items
SELECT
    description,
    sum(quantity) AS total_qty,
    count(DISTINCT order_id) AS in_orders,
    round(avg(taxable_value), 2) AS avg_mrp,
    round(avg(total_amount), 2) AS avg_paid,
    round(sum(discount), 2) AS total_discount_saved
FROM instamart_order_items
GROUP BY description
ORDER BY total_qty DESC
LIMIT 20;

-- 6.2 Highest discount items (absolute savings)
SELECT
    description,
    sum(quantity) AS qty,
    round(sum(taxable_value), 2) AS total_mrp,
    round(sum(discount), 2) AS total_discount,
    round(sum(discount) / NULLIF(sum(taxable_value), 0) * 100, 1) AS discount_pct,
    round(sum(total_amount), 2) AS paid
FROM instamart_order_items
GROUP BY description
ORDER BY total_discount DESC
LIMIT 20;

-- 6.3 Items with highest discount percentage
SELECT
    description,
    round(avg(discount / NULLIF(taxable_value, 0)) * 100, 1) AS avg_discount_pct,
    sum(quantity) AS qty,
    round(sum(discount), 2) AS total_saved
FROM instamart_order_items
WHERE taxable_value > 0
GROUP BY description
HAVING sum(quantity) >= 2
ORDER BY avg_discount_pct DESC
LIMIT 20;

-- 6.4 Category spending by HSN code
SELECT
    hsn_sac_code,
    count(DISTINCT order_id) AS orders,
    count(*) AS line_items,
    sum(quantity) AS total_qty,
    round(sum(total_amount), 2) AS total_spend
FROM instamart_order_items
GROUP BY hsn_sac_code
ORDER BY total_spend DESC;

-- 6.5 Instamart basket size analysis
SELECT
    o.order_id,
    o.date_of_invoice,
    count(i.id) AS unique_items,
    sum(i.quantity) AS total_qty,
    o.invoice_value
FROM instamart_orders o
JOIN instamart_order_items i ON o.order_id = i.order_id
GROUP BY o.order_id, o.date_of_invoice, o.invoice_value
ORDER BY total_qty DESC
LIMIT 15;


-- ============================================================
-- 7. TAX ANALYSIS
-- ============================================================

-- 7.1 Total tax paid (food)
SELECT
    round(sum(igst_amount), 2) AS total_igst,
    round(sum(cgst_amount), 2) AS total_cgst,
    round(sum(sgst_amount), 2) AS total_sgst,
    round(sum(total_taxes), 2) AS total_tax,
    round(sum(total_taxes) / NULLIF(sum(subtotal), 0) * 100, 2) AS effective_tax_rate_pct
FROM food_orders;

-- 7.2 Total tax paid (instamart — per-item breakdown)
SELECT
    round(sum(cgst_amount), 2) AS total_cgst,
    round(sum(sgst_amount), 2) AS total_sgst,
    round(sum(cess_amount), 2) AS total_cess,
    round(sum(additional_cess), 2) AS total_additional_cess,
    round(sum(cgst_amount + sgst_amount + cess_amount + additional_cess), 2) AS total_tax,
    round(
        sum(cgst_amount + sgst_amount + cess_amount + additional_cess)
        / NULLIF(sum(net_taxable_value), 0) * 100, 2
    ) AS effective_tax_rate_pct
FROM instamart_order_items;

-- 7.3 Tax by GST rate slab (instamart)
SELECT
    cgst_rate + sgst_rate AS gst_rate,
    count(*) AS items,
    round(sum(net_taxable_value), 2) AS taxable_value,
    round(sum(cgst_amount + sgst_amount), 2) AS tax_paid,
    round(sum(total_amount), 2) AS total_amount
FROM instamart_order_items
GROUP BY 1
ORDER BY 1;

-- 7.4 Monthly tax trend (combined)
SELECT
    month,
    coalesce(food_tax, 0) AS food_tax,
    coalesce(instamart_tax, 0) AS instamart_tax,
    coalesce(handling_tax, 0) AS handling_fee_tax,
    coalesce(food_tax, 0) + coalesce(instamart_tax, 0) + coalesce(handling_tax, 0) AS total_tax
FROM (
    SELECT date_trunc('month', date_of_invoice)::date AS month,
           round(sum(total_taxes), 2) AS food_tax
    FROM food_orders GROUP BY 1
) f
FULL OUTER JOIN (
    SELECT date_trunc('month', o.date_of_invoice)::date AS month,
           round(sum(i.cgst_amount + i.sgst_amount + i.cess_amount), 2) AS instamart_tax
    FROM instamart_orders o
    JOIN instamart_order_items i ON o.order_id = i.order_id
    GROUP BY 1
) im USING (month)
FULL OUTER JOIN (
    SELECT date_trunc('month', date_of_invoice)::date AS month,
           round(sum(total_taxes), 2) AS handling_tax
    FROM instamart_handling_fees GROUP BY 1
) hf USING (month)
ORDER BY month;

-- 7.5 Tax paid to each restaurant
SELECT
    restaurant_name,
    count(*) AS orders,
    round(sum(total_taxes), 2) AS total_tax,
    round(sum(invoice_total), 2) AS total_spend,
    round(sum(total_taxes) / NULLIF(sum(subtotal), 0) * 100, 2) AS tax_rate_pct
FROM food_orders
GROUP BY restaurant_name
ORDER BY total_tax DESC;


-- ============================================================
-- 8. DISCOUNT & SAVINGS ANALYSIS (INSTAMART)
-- ============================================================

-- 8.1 Total discounts saved
SELECT
    count(*) AS items_with_discount,
    round(sum(discount), 2) AS total_discount_saved,
    round(sum(taxable_value), 2) AS total_mrp,
    round(sum(total_amount), 2) AS total_paid,
    round(sum(discount) / NULLIF(sum(taxable_value), 0) * 100, 2) AS overall_discount_pct
FROM instamart_order_items
WHERE discount > 0;

-- 8.2 Monthly discount trend
SELECT
    date_trunc('month', o.date_of_invoice)::date AS month,
    round(sum(i.taxable_value), 2) AS total_mrp,
    round(sum(i.discount), 2) AS discount_saved,
    round(sum(i.total_amount), 2) AS amount_paid,
    round(sum(i.discount) / NULLIF(sum(i.taxable_value), 0) * 100, 1) AS discount_pct
FROM instamart_orders o
JOIN instamart_order_items i ON o.order_id = i.order_id
GROUP BY 1
ORDER BY 1;

-- 8.3 Discount by HSN category
SELECT
    i.hsn_sac_code,
    count(*) AS items,
    round(sum(i.discount), 2) AS total_discount,
    round(avg(i.discount / NULLIF(i.taxable_value, 0)) * 100, 1) AS avg_discount_pct
FROM instamart_order_items i
WHERE i.discount > 0 AND i.taxable_value > 0
GROUP BY 1
ORDER BY total_discount DESC
LIMIT 15;


-- ============================================================
-- 9. HANDLING FEES ANALYSIS
-- ============================================================

-- 9.1 Handling fee summary
SELECT
    count(*) AS total_orders_with_fee,
    count(*) FILTER (WHERE invoice_total > 0) AS paid_fees,
    count(*) FILTER (WHERE invoice_total = 0) AS zero_fees,
    round(sum(invoice_total), 2) AS total_fees_paid,
    round(avg(invoice_total) FILTER (WHERE invoice_total > 0), 2) AS avg_fee,
    round(sum(total_taxes), 2) AS total_tax_on_fees
FROM instamart_handling_fees;

-- 9.2 Monthly handling fee trend
SELECT
    date_trunc('month', date_of_invoice)::date AS month,
    count(*) AS orders,
    round(sum(net_assessable_value), 2) AS base_fee,
    round(sum(total_taxes), 2) AS tax,
    round(sum(invoice_total), 2) AS total_fee
FROM instamart_handling_fees
WHERE invoice_total > 0
GROUP BY 1
ORDER BY 1;

-- 9.3 Handling fee as percentage of order value
SELECT
    o.order_id,
    o.date_of_invoice,
    o.invoice_value AS order_value,
    hf.invoice_total AS handling_fee,
    round(hf.invoice_total / NULLIF(o.invoice_value, 0) * 100, 2) AS fee_pct
FROM instamart_orders o
JOIN instamart_handling_fees hf ON o.order_id = hf.order_id
WHERE hf.invoice_total > 0
ORDER BY fee_pct DESC;


-- ============================================================
-- 10. DAY & TIME PATTERNS
-- ============================================================

-- 10.1 Orders by day of week
SELECT
    extract(DOW FROM date_of_invoice) AS dow_num,
    to_char(date_of_invoice, 'Day') AS day_name,
    count(*) AS orders,
    round(sum(total), 2) AS total_spend,
    round(avg(total), 2) AS avg_order
FROM (
    SELECT date_of_invoice, invoice_total AS total FROM food_orders
    UNION ALL
    SELECT date_of_invoice, invoice_value FROM instamart_orders
) all_orders
GROUP BY 1, 2
ORDER BY 1;

-- 10.2 Food orders by day of week
SELECT
    to_char(date_of_invoice, 'Day') AS day_name,
    count(*) AS orders,
    round(avg(invoice_total), 2) AS avg_spend
FROM food_orders
GROUP BY 1, extract(DOW FROM date_of_invoice)
ORDER BY extract(DOW FROM date_of_invoice);

-- 10.3 Busiest ordering days (specific dates)
SELECT
    date_of_invoice,
    to_char(date_of_invoice, 'Day') AS day_name,
    count(*) AS orders,
    round(sum(total), 2) AS spend
FROM (
    SELECT date_of_invoice, invoice_total AS total FROM food_orders
    UNION ALL
    SELECT date_of_invoice, invoice_value FROM instamart_orders
) all_orders
GROUP BY 1, 2
HAVING count(*) > 1
ORDER BY spend DESC;

-- 10.4 Ordering frequency: days between orders
WITH all_orders AS (
    SELECT date_of_invoice, 'food' AS type FROM food_orders
    UNION ALL
    SELECT date_of_invoice, 'instamart' FROM instamart_orders
),
gaps AS (
    SELECT
        type,
        date_of_invoice,
        date_of_invoice - lag(date_of_invoice) OVER (PARTITION BY type ORDER BY date_of_invoice) AS days_gap
    FROM all_orders
)
SELECT
    type,
    round(avg(days_gap), 1) AS avg_days_between,
    min(days_gap) AS min_gap,
    max(days_gap) AS max_gap
FROM gaps
WHERE days_gap IS NOT NULL
GROUP BY type;


-- ============================================================
-- 11. ORDER VALUE DISTRIBUTION
-- ============================================================

-- 11.1 Food order value buckets
SELECT
    CASE
        WHEN invoice_total < 500 THEN '< ₹500'
        WHEN invoice_total < 1000 THEN '₹500 - ₹999'
        WHEN invoice_total < 1500 THEN '₹1000 - ₹1499'
        WHEN invoice_total < 2000 THEN '₹1500 - ₹1999'
        ELSE '₹2000+'
    END AS bucket,
    count(*) AS orders,
    round(sum(invoice_total), 2) AS total_spend,
    round(avg(invoice_total), 2) AS avg_order
FROM food_orders
GROUP BY 1
ORDER BY min(invoice_total);

-- 11.2 Instamart order value buckets
SELECT
    CASE
        WHEN invoice_value < 300 THEN '< ₹300'
        WHEN invoice_value < 600 THEN '₹300 - ₹599'
        WHEN invoice_value < 1000 THEN '₹600 - ₹999'
        WHEN invoice_value < 2000 THEN '₹1000 - ₹1999'
        ELSE '₹2000+'
    END AS bucket,
    count(*) AS orders,
    round(sum(invoice_value), 2) AS total_spend,
    round(avg(invoice_value), 2) AS avg_order
FROM instamart_orders
GROUP BY 1
ORDER BY min(invoice_value);

-- 11.3 Percentile analysis
SELECT
    'Food' AS type,
    round(percentile_cont(0.25) WITHIN GROUP (ORDER BY invoice_total)::numeric, 2) AS p25,
    round(percentile_cont(0.50) WITHIN GROUP (ORDER BY invoice_total)::numeric, 2) AS median,
    round(percentile_cont(0.75) WITHIN GROUP (ORDER BY invoice_total)::numeric, 2) AS p75,
    round(percentile_cont(0.90) WITHIN GROUP (ORDER BY invoice_total)::numeric, 2) AS p90
FROM food_orders
UNION ALL
SELECT
    'Instamart',
    round(percentile_cont(0.25) WITHIN GROUP (ORDER BY invoice_value)::numeric, 2),
    round(percentile_cont(0.50) WITHIN GROUP (ORDER BY invoice_value)::numeric, 2),
    round(percentile_cont(0.75) WITHIN GROUP (ORDER BY invoice_value)::numeric, 2),
    round(percentile_cont(0.90) WITHIN GROUP (ORDER BY invoice_value)::numeric, 2)
FROM instamart_orders;


-- ============================================================
-- 12. CUSTOMER ANALYSIS (multi-user)
-- ============================================================

-- 12.1 Per-customer spending summary
SELECT
    c.name,
    c.email,
    coalesce(f.food_orders, 0) AS food_orders,
    coalesce(f.food_spend, 0) AS food_spend,
    coalesce(im.instamart_orders, 0) AS instamart_orders,
    coalesce(im.instamart_spend, 0) AS instamart_spend,
    coalesce(f.food_spend, 0) + coalesce(im.instamart_spend, 0) AS total_spend
FROM customers c
LEFT JOIN (
    SELECT customer_id, count(*) AS food_orders, round(sum(invoice_total), 2) AS food_spend
    FROM food_orders GROUP BY 1
) f ON c.id = f.customer_id
LEFT JOIN (
    SELECT customer_id, count(*) AS instamart_orders, round(sum(invoice_value), 2) AS instamart_spend
    FROM instamart_orders GROUP BY 1
) im ON c.id = im.customer_id
ORDER BY total_spend DESC;

-- 12.2 Per-customer monthly trend
SELECT
    c.name,
    date_trunc('month', o.date_of_invoice)::date AS month,
    count(*) AS orders,
    round(sum(o.total), 2) AS spend
FROM customers c
JOIN (
    SELECT customer_id, date_of_invoice, invoice_total AS total FROM food_orders
    UNION ALL
    SELECT customer_id, date_of_invoice, invoice_value FROM instamart_orders
) o ON c.id = o.customer_id
GROUP BY 1, 2
ORDER BY 1, 2;


-- ============================================================
-- 13. HIGH-VALUE & OUTLIER DETECTION
-- ============================================================

-- 13.1 Highest food orders
SELECT
    order_id,
    date_of_invoice,
    restaurant_name,
    invoice_total,
    (SELECT count(*) FROM food_order_items WHERE order_id = fo.order_id) AS item_count
FROM food_orders fo
ORDER BY invoice_total DESC
LIMIT 10;

-- 13.2 Highest instamart orders
SELECT
    o.order_id,
    o.date_of_invoice,
    o.seller_name,
    o.invoice_value,
    count(i.id) AS item_count,
    sum(i.quantity) AS total_qty
FROM instamart_orders o
JOIN instamart_order_items i ON o.order_id = i.order_id
GROUP BY o.order_id, o.date_of_invoice, o.seller_name, o.invoice_value
ORDER BY o.invoice_value DESC
LIMIT 10;

-- 13.3 Orders significantly above average (outliers > 2x avg)
WITH avg_food AS (SELECT avg(invoice_total) AS avg_val FROM food_orders),
     avg_instamart AS (SELECT avg(invoice_value) AS avg_val FROM instamart_orders)
SELECT 'Food' AS type, order_id, date_of_invoice, restaurant_name AS name,
       invoice_total AS amount,
       round(invoice_total / af.avg_val, 1) AS times_avg
FROM food_orders, avg_food af
WHERE invoice_total > af.avg_val * 2
UNION ALL
SELECT 'Instamart', order_id, date_of_invoice, seller_name,
       invoice_value,
       round(invoice_value / ai.avg_val, 1)
FROM instamart_orders, avg_instamart ai
WHERE invoice_value > ai.avg_val * 2
ORDER BY amount DESC;


-- ============================================================
-- 14. RUNNING TOTALS & CUMULATIVE ANALYSIS
-- ============================================================

-- 14.1 Cumulative food spend over time
SELECT
    date_of_invoice,
    restaurant_name,
    invoice_total,
    sum(invoice_total) OVER (ORDER BY date_of_invoice, order_id) AS cumulative_spend
FROM food_orders
ORDER BY date_of_invoice;

-- 14.2 Cumulative instamart spend over time
SELECT
    date_of_invoice,
    seller_name,
    invoice_value,
    sum(invoice_value) OVER (ORDER BY date_of_invoice, order_id) AS cumulative_spend
FROM instamart_orders
ORDER BY date_of_invoice;

-- 14.3 Running average order value (7-order moving average)
SELECT
    date_of_invoice,
    invoice_total,
    round(avg(invoice_total) OVER (ORDER BY date_of_invoice ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS moving_avg_7
FROM food_orders
ORDER BY date_of_invoice;


-- ============================================================
-- 15. REPEAT PURCHASE ANALYSIS
-- ============================================================

-- 15.1 Food items ordered in multiple months
SELECT
    fi.description,
    count(DISTINCT date_trunc('month', fo.date_of_invoice)) AS months_ordered,
    sum(fi.quantity) AS total_qty,
    round(sum(fi.net_assessable_value), 2) AS total_spend
FROM food_order_items fi
JOIN food_orders fo ON fi.order_id = fo.order_id
WHERE fi.description NOT ILIKE '%packing%'
GROUP BY fi.description
HAVING count(DISTINCT date_trunc('month', fo.date_of_invoice)) >= 2
ORDER BY months_ordered DESC, total_spend DESC;

-- 15.2 Instamart items ordered repeatedly
SELECT
    description,
    count(DISTINCT order_id) AS orders,
    count(DISTINCT date_trunc('month', o.date_of_invoice)) AS months,
    sum(quantity) AS total_qty,
    round(sum(total_amount), 2) AS total_spend
FROM instamart_order_items i
JOIN instamart_orders o ON i.order_id = o.order_id
GROUP BY description
HAVING count(DISTINCT order_id) >= 3
ORDER BY orders DESC;

-- 15.3 Restaurant loyalty: consecutive orders from same restaurant
WITH ordered AS (
    SELECT
        order_id,
        date_of_invoice,
        restaurant_name,
        lag(restaurant_name) OVER (ORDER BY date_of_invoice, order_id) AS prev_restaurant
    FROM food_orders
)
SELECT
    restaurant_name,
    count(*) AS consecutive_repeats
FROM ordered
WHERE restaurant_name = prev_restaurant
GROUP BY restaurant_name
ORDER BY consecutive_repeats DESC;


-- ============================================================
-- 16. COST BREAKDOWN PER ORDER
-- ============================================================

-- 16.1 Full cost breakdown for each instamart order
SELECT
    o.order_id,
    o.date_of_invoice,
    o.invoice_value AS product_invoice,
    coalesce(hf.net_assessable_value, 0) AS handling_fee_base,
    coalesce(hf.total_taxes, 0) AS handling_fee_tax,
    coalesce(hf.invoice_total, 0) AS handling_fee_total,
    o.invoice_value + coalesce(hf.invoice_total, 0) AS grand_total
FROM instamart_orders o
LEFT JOIN instamart_handling_fees hf ON o.order_id = hf.order_id
ORDER BY o.date_of_invoice;

-- 16.2 Food order: items vs tax breakdown
SELECT
    fo.order_id,
    fo.date_of_invoice,
    fo.restaurant_name,
    fo.subtotal AS items_subtotal,
    fo.cgst_amount + fo.sgst_amount + fo.igst_amount AS gst,
    fo.invoice_total,
    count(fi.id) AS item_count
FROM food_orders fo
JOIN food_order_items fi ON fo.order_id = fi.order_id
GROUP BY fo.order_id, fo.date_of_invoice, fo.restaurant_name,
         fo.subtotal, fo.cgst_amount, fo.sgst_amount, fo.igst_amount, fo.invoice_total
ORDER BY fo.date_of_invoice;


-- ============================================================
-- 17. GSTIN & COMPLIANCE INSIGHTS
-- ============================================================

-- 17.1 Unique restaurant GSTINs
SELECT DISTINCT
    restaurant_name,
    restaurant_gstin,
    restaurant_fssai,
    restaurant_state
FROM food_orders
ORDER BY restaurant_name;

-- 17.2 Unique seller GSTINs
SELECT DISTINCT
    seller_name,
    seller_gstin,
    seller_fssai,
    seller_city,
    seller_state
FROM instamart_orders
ORDER BY seller_name;

-- 17.3 Tax collected by GSTIN (for ITR reference)
SELECT
    restaurant_gstin,
    restaurant_name,
    count(*) AS invoices,
    round(sum(cgst_amount), 2) AS total_cgst,
    round(sum(sgst_amount), 2) AS total_sgst,
    round(sum(total_taxes), 2) AS total_gst
FROM food_orders
GROUP BY restaurant_gstin, restaurant_name
ORDER BY total_gst DESC;
