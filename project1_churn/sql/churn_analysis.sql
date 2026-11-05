-- =====================================================================
-- PROJECT 1: Spectrum Internet Churn & Retention Analysis
-- SQL (PostgreSQL syntax; works in SQLite/DuckDB with minor changes)
-- =====================================================================

-- ---------- STEP 1: LOAD (DuckDB example: one line per table) ----------
-- CREATE TABLE customers        AS SELECT * FROM read_csv_auto('data/customers.csv');
-- CREATE TABLE monthly_usage    AS SELECT * FROM read_csv_auto('data/monthly_usage.csv');
-- CREATE TABLE billing          AS SELECT * FROM read_csv_auto('data/billing.csv');
-- CREATE TABLE support_tickets  AS SELECT * FROM read_csv_auto('data/support_tickets.csv');
-- CREATE TABLE retention_offers AS SELECT * FROM read_csv_auto('data/retention_offers.csv');

-- ---------- STEP 2: DATA QUALITY CHECKS ----------
-- 2a. Duplicate customer rows (expect ~35)
SELECT customer_id, COUNT(*) AS n
FROM customers GROUP BY customer_id HAVING COUNT(*) > 1;

-- 2b. Inconsistent market casing (e.g., 'DALLAS TX' vs 'Dallas TX')
SELECT market, COUNT(*) FROM customers GROUP BY market ORDER BY market;

-- 2c. Missing age band
SELECT COUNT(*) AS missing_age FROM customers WHERE age_band IS NULL;

-- ---------- STEP 3: CLEAN VIEW ----------
-- Lookup table standardizes market names regardless of casing
CREATE TABLE market_lookup AS
SELECT DISTINCT UPPER(market) AS market_key, market AS market_name
FROM customers WHERE market <> UPPER(market);

CREATE VIEW customers_clean AS
SELECT DISTINCT
    c.customer_id,
    m.market_name                                      AS market,
    UPPER(RIGHT(c.market,2))                           AS state,
    CAST(c.signup_date AS DATE)                        AS signup_date,
    c.plan_name, c.promo_price, c.list_price,
    CAST(c.promo_end_date AS DATE)                     AS promo_end_date,
    c.has_spectrum_mobile, c.has_spectrum_tv, c.autopay, c.paperless,
    c.equipment, COALESCE(c.age_band,'Unknown')        AS age_band,
    c.competitor_fiber_available,
    c.churned, CAST(c.churn_date AS DATE) AS churn_date, c.churn_reason,
    (DATE '2025-12-31' - CAST(c.signup_date AS DATE)) / 365.0 AS tenure_years,
    CAST(c.promo_end_date AS DATE) BETWEEN DATE '2025-01-01' AND DATE '2025-12-31' AS promo_rolled_2025,
    c.list_price - c.promo_price                       AS price_jump
FROM customers c
JOIN market_lookup m ON UPPER(c.market) = m.market_key;
-- TIP: the cleanest market fix is a 10-row lookup table joined on UPPER(market).

-- ---------- STEP 4: KPIs ----------
-- 4a. Overall 2025 churn rate
SELECT ROUND(AVG(CASE WHEN churned THEN 1.0 ELSE 0 END)*100,1) AS churn_rate_pct
FROM customers_clean;

-- 4b. Monthly churn trend
SELECT DATE_TRUNC('month', churn_date) AS month, COUNT(*) AS disconnects
FROM customers_clean WHERE churned GROUP BY 1 ORDER BY 1;

-- 4c. Churn by key driver (run each GROUP BY separately)
SELECT promo_rolled_2025, COUNT(*) subs,
       ROUND(AVG(CASE WHEN churned THEN 1.0 ELSE 0 END)*100,1) churn_pct
FROM customers_clean GROUP BY 1;

SELECT competitor_fiber_available, has_spectrum_mobile,
       COUNT(*) subs, ROUND(AVG(CASE WHEN churned THEN 1.0 ELSE 0 END)*100,1) churn_pct
FROM customers_clean GROUP BY 1,2 ORDER BY 4 DESC;

SELECT equipment, COUNT(*) subs,
       ROUND(AVG(CASE WHEN churned THEN 1.0 ELSE 0 END)*100,1) churn_pct
FROM customers_clean GROUP BY 1 ORDER BY 3 DESC;

-- 4d. Churn reasons
SELECT churn_reason, COUNT(*) n,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) pct
FROM customers_clean WHERE churned GROUP BY 1 ORDER BY 2 DESC;

-- ---------- STEP 5: CUSTOMER-LEVEL FEATURE TABLE (for the model + Power BI) ----------
CREATE TABLE churn_features AS
WITH u AS (
  SELECT customer_id,
         AVG(data_used_gb)     AS avg_gb,
         AVG(avg_speed_mbps)   AS avg_speed,
         AVG(outage_minutes)   AS avg_outage_min,
         AVG(wifi_disconnects) AS avg_disconnects
  FROM monthly_usage GROUP BY 1),
b AS (
  SELECT customer_id,
         SUM(CASE WHEN days_late > 0 THEN 1 ELSE 0 END) AS late_payments,
         SUM(amount_billed) AS total_billed
  FROM billing GROUP BY 1),
t AS (
  SELECT customer_id,
         COUNT(*) AS tickets,
         SUM(CASE WHEN NOT resolved_first_contact THEN 1 ELSE 0 END) AS unresolved_tickets,
         AVG(csat_score) AS avg_csat
  FROM support_tickets GROUP BY 1)
SELECT c.*, u.avg_gb, u.avg_speed, u.avg_outage_min, u.avg_disconnects,
       COALESCE(b.late_payments,0) late_payments, b.total_billed,
       COALESCE(t.tickets,0) tickets, COALESCE(t.unresolved_tickets,0) unresolved_tickets, t.avg_csat
FROM customers_clean c
LEFT JOIN u USING (customer_id)
LEFT JOIN b USING (customer_id)
LEFT JOIN t USING (customer_id);

-- ---------- STEP 6: RETENTION OFFER A/B TEST ----------
SELECT test_group,
       COUNT(*) AS customers,
       ROUND(AVG(CASE WHEN churned_within_90d THEN 1.0 ELSE 0 END)*100,1) AS churn_90d_pct,
       MAX(offer_cost_monthly) AS cost_per_month
FROM retention_offers GROUP BY 1 ORDER BY 3;

-- Saves vs control and cost per save (assumes ~$70 ARPU, 12-month offer)
WITH r AS (
  SELECT test_group, COUNT(*) n,
         AVG(CASE WHEN churned_within_90d THEN 1.0 ELSE 0 END) churn,
         MAX(offer_cost_monthly) cost
  FROM retention_offers GROUP BY 1),
ctl AS (SELECT churn AS ctl_churn FROM r WHERE test_group='Control')
SELECT test_group,
       ROUND((ctl_churn - churn)*n)                        AS est_saves,
       ROUND(cost*12*n*(1-churn))                          AS annual_offer_cost,
       ROUND(cost*12*n*(1-churn) / NULLIF((ctl_churn-churn)*n,0)) AS cost_per_save,
       70*12*3                                             AS est_lifetime_value_per_save  -- ~3 yrs x $70/mo
FROM r, ctl WHERE test_group <> 'Control';

-- ---------- STEP 7: REVENUE AT RISK ----------
SELECT state,
       COUNT(*) FILTER (WHERE churned)              AS lost_subs,
       ROUND(SUM(CASE WHEN churned THEN list_price*12 ELSE 0 END)) AS annualized_revenue_lost
FROM customers_clean GROUP BY 1 ORDER BY 3 DESC;
