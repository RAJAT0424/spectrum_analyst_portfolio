import duckdb

con = duckdb.connect("spectrum.duckdb")

tables = {
    "customers":        "project1_churn/data/customers.csv",
    "monthly_usage":    "project1_churn/data/monthly_usage.csv",
    "billing":          "project1_churn/data/billing.csv",
    "support_tickets":  "project1_churn/data/support_tickets.csv",
    "retention_offers": "project1_churn/data/retention_offers.csv",
    "calls":            "project2_care_ops/data/calls.csv",
    "agents":           "project2_care_ops/data/agents.csv",
    "outages":          "project2_care_ops/data/outages.csv",
    "truck_rolls":      "project2_care_ops/data/truck_rolls.csv",
}
for name, path in tables.items():
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM read_csv_auto('{path}')")
    n = con.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
    print(f"{name:<18} {n:>9,} rows")
con.close()
