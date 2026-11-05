"""Synthetic datasets for two Charter/Spectrum-style data analyst portfolio projects.
All data is fictional. Signals are planted so the analysis produces real findings."""
import numpy as np, pandas as pd, os
rng = np.random.default_rng(42)
os.makedirs("project1_churn/data", exist_ok=True)
os.makedirs("project2_care_ops/data", exist_ok=True)

MARKETS = {"Stamford CT":"CT","Hartford CT":"CT","New York City NY":"NY","Albany NY":"NY",
           "Charlotte NC":"NC","Raleigh NC":"NC","Dallas TX":"TX","Austin TX":"TX",
           "Columbus OH":"OH","Los Angeles CA":"CA"}
mkts = list(MARKETS)
START, END = pd.Timestamp("2025-01-01"), pd.Timestamp("2025-12-31")
months = pd.date_range("2025-01-01", "2025-12-01", freq="MS")

# ---------------- PROJECT 1: CHURN ----------------
N = 20000
plans = {"Internet Premier 500":(49.99,500),"Internet Ultra 1 Gig":(69.99,1000),"Internet Gig 2":(89.99,2000),"Internet Assist":(24.99,100)}
pname = rng.choice(list(plans), N, p=[.48,.32,.10,.10])
signup = pd.to_datetime(rng.integers(pd.Timestamp("2019-01-01").value//10**9, pd.Timestamp("2024-12-31").value//10**9, N), unit="s").normalize()
promo_len = rng.choice([12,24], N, p=[.7,.3])
promo_end = signup + pd.to_timedelta(promo_len*30, unit="D")
# many promos roll off during 2025
reset = rng.random(N) < .35
promo_end = promo_end.where(~reset, pd.to_datetime(rng.integers(START.value//10**9, END.value//10**9, N), unit="s").normalize())
cust = pd.DataFrame({
    "customer_id":[f"C{100000+i}" for i in range(N)],
    "market":rng.choice(mkts,N,p=[.08,.07,.18,.05,.1,.08,.14,.1,.08,.12]),
    "signup_date":signup.date,"plan_name":pname,
    "promo_price":[plans[p][0] for p in pname],
    "promo_end_date":promo_end.date,
    "has_spectrum_mobile":rng.random(N)<.28,"has_spectrum_tv":rng.random(N)<.22,
    "autopay":rng.random(N)<.55,"paperless":rng.random(N)<.62,
    "equipment":rng.choice(["Advanced WiFi Router","Legacy Router","Customer-Owned"],N,p=[.6,.25,.15]),
    "age_band":rng.choice(["18-24","25-34","35-44","45-54","55-64","65+"],N,p=[.08,.22,.22,.19,.16,.13]),
})
cust["state"] = cust.market.map(MARKETS)
cust["list_price"] = (cust.promo_price*rng.uniform(1.25,1.45,N)).round(2)
cust.loc[cust.plan_name=="Internet Assist","list_price"] = 24.99
# competitor fiber presence by market
fiber = {"Dallas TX":.9,"Austin TX":.85,"Charlotte NC":.7,"Raleigh NC":.75,"Los Angeles CA":.6,"New York City NY":.5,"Columbus OH":.45,"Stamford CT":.3,"Hartford CT":.25,"Albany NY":.2}
cust["competitor_fiber_available"] = rng.random(N) < cust.market.map(fiber)

# monthly usage + outages
rows=[]
mkt_outage = {m:rng.uniform(5,40) for m in mkts}
for m in months:
    mu = cust.market.map(mkt_outage).values * np.where(cust.equipment=="Legacy Router",1.8,1)
    rows.append(pd.DataFrame({"customer_id":cust.customer_id,"month":m.date(),
        "data_used_gb":np.clip(rng.gamma(4,140,N)*(1+.15*(m.month/12)),5,4000).round(1),
        "avg_speed_mbps":(cust.plan_name.map(lambda p:plans[p][1])*rng.uniform(.6,1.05,N)*np.where(cust.equipment=="Legacy Router",.7,1)).round(0),
        "outage_minutes":rng.poisson(mu).astype(int),
        "wifi_disconnects":rng.poisson(np.where(cust.equipment=="Legacy Router",9,3))}))
usage = pd.concat(rows, ignore_index=True)

# churn model (planted drivers)
agg = usage.groupby("customer_id").agg(out=("outage_minutes","mean"),disc=("wifi_disconnects","mean")).reset_index()
c = cust.merge(agg,on="customer_id")
tenure_yrs = (END - pd.to_datetime(c.signup_date)).dt.days/365
pe = pd.to_datetime(c.promo_end_date)
rolled = (pe>=START)&(pe<=END)
logit = (-2.2 + 1.1*rolled + .9*c.competitor_fiber_available - .8*c.has_spectrum_mobile - .4*c.has_spectrum_tv
         - .5*c.autopay + .025*(c.out-20) + .08*(c.disc-4) - .18*np.minimum(tenure_yrs,6)
         + .4*(c.plan_name=="Internet Gig 2") + .3*c.age_band.isin(["18-24","25-34"]))
p = 1/(1+np.exp(-logit))
churn = rng.random(N) < p
cdate = np.where(rolled, pe + pd.to_timedelta(rng.integers(5,75,N),unit="D"),
                 pd.to_datetime(rng.integers(START.value//10**9, END.value//10**9, N),unit="s"))
cdate = pd.Series(pd.to_datetime(cdate)).dt.normalize()
cdate = cdate.where(cdate<=END, END)
reasons = np.where(rolled & (rng.random(N)<.6),"Price increase after promo",
          np.where(c.competitor_fiber_available & (rng.random(N)<.5),"Switched to competitor",
          rng.choice(["Service reliability","Moved out of footprint","Slow speeds","Customer service experience","Other"],N,p=[.3,.3,.15,.15,.1])))
cust["churned"]=churn
cust["churn_date"]=pd.Series(cdate.dt.date.values).where(churn,None)
cust["churn_reason"]=pd.Series(reasons).where(churn,None)
# trim usage after churn
usage = usage.merge(cust[["customer_id","churn_date"]],on="customer_id")
usage = usage[usage.churn_date.isna() | (pd.to_datetime(usage.month) <= pd.to_datetime(usage.churn_date))].drop(columns="churn_date")

# billing
bill = usage[["customer_id","month"]].merge(cust[["customer_id","promo_price","list_price","promo_end_date","autopay"]],on="customer_id")
bill["amount_billed"] = np.where(pd.to_datetime(bill.month) > pd.to_datetime(bill.promo_end_date), bill.list_price, bill.promo_price)
bill["amount_billed"] = (bill.amount_billed + rng.choice([0,0,0,10,15],len(bill))).round(2)
late = rng.random(len(bill)) < np.where(bill.autopay,.02,.11)
bill["days_late"] = np.where(late, rng.integers(1,45,len(bill)), 0)
bill["amount_paid"] = np.where(rng.random(len(bill))<.015,0,bill.amount_billed)
bill = bill[["customer_id","month","amount_billed","amount_paid","days_late"]]

# tickets
tk_n = 26000
tk = pd.DataFrame({"ticket_id":[f"T{500000+i}" for i in range(tk_n)],
    "customer_id":rng.choice(cust.customer_id,tk_n,p=(lambda w:w/w.sum())(np.where(cust.churned,3,1)*np.where(cust.equipment=="Legacy Router",1.7,1)))})
tk["created_date"]=pd.to_datetime(rng.integers(START.value//10**9,END.value//10**9,tk_n),unit="s").date
tk["category"]=rng.choice(["Slow Speeds","Intermittent Connection","Billing Question","Price Increase","Equipment","Outage","Move/Transfer","Cancel Request"],tk_n,p=[.18,.17,.15,.13,.12,.12,.07,.06])
tk["channel"]=rng.choice(["Phone","Chat","Store","App"],tk_n,p=[.55,.2,.1,.15])
tk["resolved_first_contact"]=rng.random(tk_n)<.68
tk["csat_score"]=np.clip(np.round(rng.normal(np.where(tk.resolved_first_contact,4.1,2.9),.8)),1,5).astype(int)

# retention offers (A/B test)
cand = cust[cust.promo_end_date.apply(lambda d: START.date()<=d<=END.date())].sample(4000,random_state=1)
off = pd.DataFrame({"customer_id":cand.customer_id.values,"offer_date":pd.to_datetime(cand.promo_end_date.values)-pd.Timedelta(days=30)})
off["test_group"]=rng.choice(["Control","Discount $10x12mo","Free Speed Upgrade","Mobile Line Free 1yr"],4000)
eff={"Control":0,"Discount $10x12mo":-.45,"Free Speed Upgrade":-.25,"Mobile Line Free 1yr":-.55}
base = cust.set_index("customer_id").loc[off.customer_id,"churned"].values
save = rng.random(4000) < off.test_group.map(eff).abs().values*.55
off["churned_within_90d"] = base & ~save
off["offer_cost_monthly"] = off.test_group.map({"Control":0,"Discount $10x12mo":10,"Free Speed Upgrade":6,"Mobile Line Free 1yr":14})
off["offer_date"]=off.offer_date.dt.date
cust.loc[cust.customer_id.isin(off.customer_id) , "churned"] = cust.loc[cust.customer_id.isin(off.customer_id),"customer_id"].map(off.set_index("customer_id").churned_within_90d)
cust.loc[~cust.churned.astype(bool),["churn_date","churn_reason"]] = None

# a little real-world mess
cust.loc[rng.choice(N,120,replace=False),"age_band"]=None
cust.loc[rng.choice(N,60,replace=False),"market"]=cust.market.sample(60,random_state=3).str.upper().values
cust = pd.concat([cust,cust.sample(35,random_state=5)])  # duplicate rows

cust.to_csv("project1_churn/data/customers.csv",index=False)
usage.to_csv("project1_churn/data/monthly_usage.csv",index=False)
bill.to_csv("project1_churn/data/billing.csv",index=False)
tk.to_csv("project1_churn/data/support_tickets.csv",index=False)
off.to_csv("project1_churn/data/retention_offers.csv",index=False)

# ---------------- PROJECT 2: CARE & FIELD OPS ----------------
centers=["Stamford CT","Charlotte NC","St. Louis MO","El Paso TX","Remote"]
agents=pd.DataFrame({"agent_id":[f"A{1000+i}" for i in range(400)],"center":rng.choice(centers,400,p=[.2,.25,.2,.2,.15]),
    "tenure_months":rng.integers(1,96,400),"team_lead":rng.choice([f"TL{i:02d}" for i in range(1,26)],400)})
agents["hire_cohort"]=np.where(agents.tenure_months<6,"New (<6mo)",np.where(agents.tenure_months<24,"Developing","Experienced"))

out_n=420
outs=pd.DataFrame({"outage_id":[f"O{7000+i}" for i in range(out_n)],"market":rng.choice(mkts,out_n)})
outs["start_time"]=pd.to_datetime(rng.integers(START.value//10**9,END.value//10**9,out_n),unit="s")
dur=rng.gamma(2,90,out_n)
outs["end_time"]=outs.start_time+pd.to_timedelta(dur,unit="m")
outs["cause"]=rng.choice(["Fiber Cut","Power","Equipment Failure","Weather","Planned Maintenance"],out_n,p=[.25,.2,.3,.15,.1])
outs["customers_affected"]=rng.integers(200,25000,out_n)
outs["proactive_notification_sent"]=rng.random(out_n)<.45

CALLS=90000
ts=pd.to_datetime(rng.integers(START.value//10**9,END.value//10**9,CALLS),unit="s")
hr=rng.choice(range(7,23),CALLS,p=(lambda w:w/w.sum())(np.array([3,6,9,10,9,8,8,7,7,8,9,8,6,4,3,2],float)))
ts=ts.normalize()+pd.to_timedelta(hr,unit="h")+pd.to_timedelta(rng.integers(0,3600,CALLS),unit="s")
calls=pd.DataFrame({"call_id":[f"CL{3000000+i}" for i in range(CALLS)],"call_start":ts,
    "customer_id":rng.choice(cust.customer_id.unique(),CALLS),"market":rng.choice(mkts,CALLS),
    "agent_id":rng.choice(agents.agent_id,CALLS)})
calls["call_reason"]=rng.choice(["No Internet","Slow Speeds","Billing Dispute","Payment","Equipment Setup","Appointment Change","Upgrade/Sales","Cancel/Retention","WiFi Help"],CALLS,p=[.17,.14,.15,.08,.1,.08,.1,.07,.11])
# outage-driven calls
oc=[]
for _,o in outs.iterrows():
    k=int(o.customers_affected*(.0025 if o.proactive_notification_sent else .009))
    oc.append(pd.DataFrame({"call_start":o.start_time+pd.to_timedelta(rng.integers(0,int(max(30,(o.end_time-o.start_time).total_seconds()/60)),k),unit="m"),"market":o.market,"call_reason":"No Internet"}))
oc=pd.concat(oc,ignore_index=True)
oc["call_id"]=[f"CL{4000000+i}" for i in range(len(oc))]
oc["customer_id"]=rng.choice(cust.customer_id.unique(),len(oc)); oc["agent_id"]=rng.choice(agents.agent_id,len(oc))
calls=pd.concat([calls,oc],ignore_index=True)
calls=calls.merge(agents[["agent_id","center","tenure_months"]],on="agent_id")
calls["ivr_contained"]=False
calls["queue_wait_sec"]=np.clip(rng.gamma(2,90,len(calls))*np.where(calls.call_start.dt.hour.isin([9,10,11]),1.8,1),5,3600).astype(int)
base_aht={"No Internet":540,"Slow Speeds":620,"Billing Dispute":720,"Payment":240,"Equipment Setup":800,"Appointment Change":300,"Upgrade/Sales":660,"Cancel/Retention":780,"WiFi Help":580}
calls["handle_time_sec"]=(calls.call_reason.map(base_aht)*rng.uniform(.6,1.5,len(calls))*np.where(calls.tenure_months<6,1.3,1)).astype(int)
calls["transferred"]=rng.random(len(calls))<np.where(calls.tenure_months<6,.28,.14)
fcr_p=np.where(calls.tenure_months<6,.58,.76)-np.where(calls.transferred,.2,0)
calls["resolved_first_contact"]=rng.random(len(calls))<fcr_p
calls["truck_roll_created"]=rng.random(len(calls))<np.where(calls.call_reason.isin(["No Internet","Slow Speeds","WiFi Help"]),np.where(calls.tenure_months<6,.30,.17),.02)
calls["csat_score"]=np.clip(np.round(rng.normal(4.2-.6*(~calls.resolved_first_contact)-.4*calls.transferred-calls.queue_wait_sec/1500,.8)),1,5).astype(int)
calls=calls.sort_values("call_start").reset_index(drop=True)
calls["call_start"]=calls.call_start.dt.strftime("%Y-%m-%d %H:%M:%S")
calls=calls.drop(columns=["center","tenure_months"])

tr=calls[calls.truck_roll_created][["call_id","customer_id","market","call_start","call_reason"]].copy()
tr["job_id"]=[f"J{800000+i}" for i in range(len(tr))]
tr["scheduled_date"]=(pd.to_datetime(tr.call_start)+pd.to_timedelta(rng.integers(1,6,len(tr)),unit="D")).dt.date
tr["job_type"]=rng.choice(["Trouble Call","Equipment Swap","Line Repair"],len(tr),p=[.6,.25,.15])
tr["tech_id"]=rng.choice([f"TECH{i:03d}" for i in range(1,180)],len(tr))
tr["no_fault_found"]=rng.random(len(tr))<np.where(tr.call_reason=="WiFi Help",.55,.3)
tr["resolution_code"]=np.where(tr.no_fault_found,rng.choice(["NFF - Customer Education","NFF - Inside WiFi","NFF - Unable to Duplicate"],len(tr)),rng.choice(["Replaced Modem","Replaced Router","Repaired Drop","Tap/Amp Repair","Re-terminated Connector"],len(tr)))
tr["missed_appointment"]=rng.random(len(tr))<.07
tr["repeat_truck_roll_30d"]=rng.random(len(tr))<np.where(tr.no_fault_found,.22,.09)
tr["job_cost_usd"]=np.round(rng.normal(np.where(tr.job_type=="Line Repair",210,135),25),2)
tr=tr[["job_id","call_id","customer_id","market","scheduled_date","job_type","tech_id","resolution_code","no_fault_found","missed_appointment","repeat_truck_roll_30d","job_cost_usd"]]

calls.to_csv("project2_care_ops/data/calls.csv",index=False)
agents.to_csv("project2_care_ops/data/agents.csv",index=False)
outs.to_csv("project2_care_ops/data/outages.csv",index=False)
tr.to_csv("project2_care_ops/data/truck_rolls.csv",index=False)

for f in ["project1_churn/data","project2_care_ops/data"]:
    for x in sorted(os.listdir(f)):
        print(f, x, len(pd.read_csv(f"{f}/{x}")))
