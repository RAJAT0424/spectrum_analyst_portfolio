# Rajat Karki — Data & Business Analytics Portfolio

Two end-to-end analytics projects on a cable broadband business (modeled on Spectrum), built with **SQL, Python and Power BI**.

> All data is synthetic and generated for this portfolio. Not affiliated with Charter Communications.

## Project 1 — Internet Churn & Retention ✅
**Question:** Why are broadband customers leaving, who will leave next, and which save offer is worth the money?

**Results**
- 2025 churn of **13.2%**, putting **$2.52M** in annual revenue at risk
- Promo roll-off (19.3% vs 8.2% churn) and fiber competition (16.2% vs 9.1%) are the biggest drivers; a Spectrum Mobile bundle **cuts churn in half** (7.6% vs 15.4%)
- Churn model (random forest, **AUC 0.90**): the riskiest 20% of customers include **74% of churners**; **1,431 active customers** are flagged high-risk
- Retention A/B test (4,000 customers): all three offers reduced 90-day churn from **20.2% to ~16%** (p < 0.05). The **free speed upgrade** gives the best return at **$1,678 per save** vs a $2,520 customer value

**Recommendation:** Contact high-risk customers 30–45 days before their promo ends, use the speed upgrade for Medium-risk customers and the Mobile line offer only for High-risk customers in fiber markets, and replace legacy routers proactively.

![Executive summary](project1_churn/images/dashboard_1_executive_summary.png)

[See the full project →](project1_churn/)

## Project 2 — Customer Care & Field Operations 🚧 In progress
**Question:** How do we cut avoidable technician visits and outage call spikes?

## Tools
SQL (DuckDB) · Python (pandas, scikit-learn, matplotlib) · Power BI (DAX) · Jupyter · Git

## Repo structure
- `project1_churn/` — data, SQL, notebooks (01–04), Power BI dashboard, images
- `project2_care_ops/` — data and SQL (analysis in progress)
- `load_data.py` — loads all CSVs into a local DuckDB database
- `generate_data.py` — re-creates every synthetic dataset
