"""Project 1 - Churn prediction model.
Run from the project1_churn folder:  python python/churn_model.py
Outputs: model metrics, top churn drivers, and a scored customer list (outputs/churn_scores.csv)
that feeds the Power BI 'At-Risk Customers' page."""
import os, pandas as pd, numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, classification_report

os.makedirs("outputs", exist_ok=True)

# ---- 1. Load & clean ----
c = pd.read_csv("data/customers.csv").drop_duplicates()
c["market"] = c["market"].str.title().str.replace(r" (\w\w)$", lambda m: " " + m.group(1).upper(), regex=True)
c["age_band"] = c["age_band"].fillna("Unknown")
for col in ["signup_date", "promo_end_date"]:
    c[col] = pd.to_datetime(c[col])
c["tenure_years"] = (pd.Timestamp("2025-12-31") - c.signup_date).dt.days / 365
c["promo_rolled_2025"] = c.promo_end_date.between("2025-01-01", "2025-12-31")
c["price_jump"] = c.list_price - c.promo_price

# ---- 2. Feature engineering from usage / billing / tickets ----
u = pd.read_csv("data/monthly_usage.csv").groupby("customer_id").agg(
    avg_gb=("data_used_gb", "mean"), avg_speed=("avg_speed_mbps", "mean"),
    avg_outage_min=("outage_minutes", "mean"), avg_disconnects=("wifi_disconnects", "mean"))
b = pd.read_csv("data/billing.csv").assign(late=lambda d: d.days_late > 0).groupby("customer_id").agg(late_payments=("late", "sum"))
t = pd.read_csv("data/support_tickets.csv").groupby("customer_id").agg(
    tickets=("ticket_id", "count"), avg_csat=("csat_score", "mean"))
df = c.merge(u, on="customer_id", how="left").merge(b, on="customer_id", how="left").merge(t, on="customer_id", how="left")
df[["tickets", "late_payments"]] = df[["tickets", "late_payments"]].fillna(0)
df["avg_csat"] = df["avg_csat"].fillna(df["avg_csat"].median())

features = ["tenure_years", "promo_rolled_2025", "price_jump", "has_spectrum_mobile", "has_spectrum_tv",
            "autopay", "paperless", "competitor_fiber_available", "avg_gb", "avg_speed", "avg_outage_min",
            "avg_disconnects", "late_payments", "tickets", "avg_csat"]
X = pd.get_dummies(df[features + ["plan_name", "equipment", "age_band"]], drop_first=True).astype(float)
y = df["churned"].astype(int)

# ---- 3. Train / test ----
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, stratify=y, random_state=7)
lr = LogisticRegression(max_iter=2000, class_weight="balanced").fit((Xtr - Xtr.mean()) / Xtr.std(), ytr)
rf = RandomForestClassifier(n_estimators=300, min_samples_leaf=20, class_weight="balanced", random_state=7).fit(Xtr, ytr)

p_lr = lr.predict_proba((Xte - Xtr.mean()) / Xtr.std())[:, 1]
p_rf = rf.predict_proba(Xte)[:, 1]
print(f"Baseline churn rate: {y.mean():.1%}")
print(f"Logistic Regression AUC: {roc_auc_score(yte, p_lr):.3f}")
print(f"Random Forest AUC:       {roc_auc_score(yte, p_rf):.3f}")
print(classification_report(yte, (p_rf > 0.5).astype(int), digits=3))

# ---- 4. Drivers (standardized logistic coefficients = easy to explain in an interview) ----
coef = pd.Series(lr.coef_[0], index=X.columns).sort_values()
print("\nTop factors INCREASING churn:\n", coef.tail(6).round(2).to_string())
print("\nTop factors DECREASING churn:\n", coef.head(6).round(2).to_string())

# ---- 5. Lift: how much churn do we catch by targeting the top 20% riskiest? ----
lift = pd.DataFrame({"y": yte.values, "p": p_rf}).sort_values("p", ascending=False)
top = lift.head(int(len(lift) * .2))
print(f"\nTop 20% risk-scored customers contain {top.y.sum() / lift.y.sum():.0%} of all churners")

# ---- 6. Score every active customer for the retention team ----
df["churn_risk_score"] = rf.predict_proba(X)[:, 1].round(3)
df["risk_tier"] = pd.cut(df.churn_risk_score, [0, .3, .6, 1], labels=["Low", "Medium", "High"], include_lowest=True)
df[["customer_id", "market", "state", "plan_name", "equipment", "promo_end_date", "list_price",
    "churned", "churn_risk_score", "risk_tier"]].to_csv("outputs/churn_scores.csv", index=False)
print("Saved outputs/churn_scores.csv")
