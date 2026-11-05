# Project 1 — Spectrum Internet Churn & Retention Analytics

> **Portfolio project (synthetic data).** All customers, prices and results are fictional and generated for practice. Not affiliated with Charter Communications.

## 1. The business scenario

You are a Data Analyst on the **Consumer Retention** team for a large U.S. cable broadband provider (modeled on Spectrum). Leadership noticed broadband disconnects rising in 2025, especially in Texas and the Carolinas where fiber competitors are expanding. Many subscribers also rolled off their 12- or 24-month promotional price this year and saw a $15–$35 increase.

The VP of Retention asks you three questions:

1. **Why are customers leaving?** Which factors drive churn the most?
2. **Who is likely to leave next?** Give the retention team a ranked list of at-risk customers.
3. **Which save offer should we use?** A 90-day pilot tested three retention offers against a control group. Which one is worth rolling out?

## 2. Datasets (`data/`)

| File | Rows | Grain | Key columns |
|---|---|---|---|
| `customers.csv` | 20,035 | 1 row per subscriber (35 dupes planted) | plan_name, promo_price, list_price, promo_end_date, has_spectrum_mobile, has_spectrum_tv, autopay, equipment, competitor_fiber_available, **churned**, churn_date, churn_reason |
| `monthly_usage.csv` | ~227K | customer × month (2025) | data_used_gb, avg_speed_mbps, outage_minutes, wifi_disconnects |
| `billing.csv` | ~227K | customer × month | amount_billed, amount_paid, days_late |
| `support_tickets.csv` | 26,000 | 1 row per ticket | category, channel, resolved_first_contact, csat_score |
| `retention_offers.csv` | 4,000 | 1 row per customer in the A/B test | test_group, offer_cost_monthly, churned_within_90d |

**Planted data-quality issues** (find and fix these — interviewers love this): duplicate customer rows, inconsistent market casing (`DALLAS TX` vs `Dallas TX`), 120 missing `age_band` values, and churned customers having fewer billing months (a trap — see §6).

## 3. Tools
SQL (PostgreSQL / DuckDB / SQL Server) → Python (pandas, scikit-learn) → Power BI (or Tableau) → GitHub.

## 4. End-to-end steps

**Step 1 — Load.** Import the five CSVs into a database (DuckDB is free and easiest; Postgres or SQL Server also work). Load commands are at the top of `sql/churn_analysis.sql`.

**Step 2 — Profile & clean (SQL §2–3).** Count duplicates, standardize market names with a lookup table, fill unknown age bands, and cast dates. Build `customers_clean` with derived fields: `tenure_years`, `promo_rolled_2025`, `price_jump`.

**Step 3 — Exploratory KPIs (SQL §4).** Overall churn rate, monthly disconnect trend, churn by promo roll-off, competitor fiber, bundle (Mobile/TV), equipment, and churn reasons.

**Step 4 — Feature table (SQL §5).** Join usage, billing and ticket aggregates to one row per customer → `churn_features`. This feeds both the model and Power BI.

**Step 5 — Predictive model (`python/churn_model.py`).** Logistic regression (explainable drivers) + random forest (scoring). Evaluate with AUC, precision/recall, and **lift** ("the riskiest 20% of customers contain X% of churners"). Export `outputs/churn_scores.csv` with a risk score and Low/Medium/High tier for every customer.

**Step 6 — A/B test the save offers (SQL §6).** Compare 90-day churn for each offer vs. control, calculate saves, offer cost, and **cost per save vs. customer lifetime value**. Optional: run a two-proportion z-test in Python to check significance.

**Step 7 — Revenue at risk (SQL §7).** Annualized revenue lost by state.

**Step 8 — Power BI dashboard (4 pages).**
- *Executive Summary:* KPI cards (subscribers, churn %, revenue lost, saves), monthly churn line, churn by state map.
- *Churn Drivers:* bar charts by promo roll-off, fiber competition, bundle, equipment; churn reason donut; slicers for market/plan.
- *At-Risk Customers:* table from `churn_scores.csv`, filter by risk tier and upcoming promo end date.
- *Offer Test:* churn % by test group, cost per save, recommendation callout.

**Step 9 — Recommendations memo** (1 page) + **GitHub repo** with this README, SQL, notebook, dashboard screenshots.

## 5. What you should find (answer key — try first, then check)

| Finding | Result in this data |
|---|---|
| Overall 2025 churn | **≈13.2%** |
| Promo rolled off in 2025 vs. not | **19.3% vs 8.2%** churn |
| Fiber competitor available vs. not | **16.2% vs 9.1%** |
| Has Spectrum Mobile vs. not | **7.6% vs 15.4%** (bundling halves churn) |
| Legacy router vs. Advanced WiFi | **21.2% vs 10.7%** |
| #1 churn reason | "Price increase after promo" (~42%), then "Switched to competitor" (~22%) |
| Model | AUC ≈ 0.90; top 20% riskiest hold ~75% of churners |
| Offer test (90-day churn) | Control 20.2%, $10 discount 15.9%, Free Mobile line 15.7%, Speed upgrade 16.7% |

**Recommended story:** Promo roll-off is the single biggest lever. Contact customers **30–45 days before promo end**, prioritized by risk score. Lead with the **Mobile line offer** (best save rate and creates a bundle that keeps lowering churn), use the **speed upgrade** as the low-cost option for medium-risk customers, and **replace legacy routers** proactively in high-churn markets. Blanket offers to everyone cost more than they save — targeting only High-risk customers is what makes the math work.

## 6. Analyst watch-outs (great interview talking points)
- **Target leakage:** tickets include "Cancel Request" — a customer calling to cancel is not a *predictor*, it's the outcome. Rebuild the model excluding cancel tickets and tickets in the 30 days before churn; AUC will drop to a more honest number.
- **Exposure bias:** `late_payments` looks protective only because churned customers have fewer billing months. Normalize to *late payments per month active*.
- **Cost per save** must be compared to lifetime value, not one month of revenue.

## 7. Resume bullets (edit numbers to match your final results)
- Built an end-to-end churn analytics solution on 20K+ broadband subscribers and 450K+ usage/billing records using SQL, Python and Power BI, identifying promo roll-off, fiber competition and legacy equipment as top churn drivers.
- Developed a churn prediction model (AUC 0.90) where the top 20% of risk-scored customers captured ~75% of churners, enabling targeted retention outreach.
- Analyzed a 4,000-customer retention offer A/B test; recommended a targeted mobile-bundle offer that reduced 90-day churn from 20% to 16% versus control.

## 8. 30-second interview pitch
"I built a churn project modeled on a cable broadband business. I cleaned five data sources in SQL, found that promo roll-off nearly doubles churn and that Mobile bundling cuts it in half, built a model so the retention team could focus on the riskiest 20% of customers who make up three-quarters of churn, and evaluated an A/B test of save offers using cost per save against lifetime value. I also caught two data traps — target leakage and exposure bias — which changed how I'd present the model."
