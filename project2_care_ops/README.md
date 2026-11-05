# Project 2 — Spectrum Customer Care & Field Operations Analytics
### Reducing avoidable truck rolls and outage call spikes

> **Portfolio project (synthetic data).** All calls, agents, outages and costs are fictional. Not affiliated with Charter Communications.

## 1. The business scenario

You are a Data Analyst supporting **Customer Operations** (call centers + field technicians) at a large cable provider. Every technician visit ("truck roll") costs ~$135–$210, and 2025 field spend is over budget. Call centers are also missing service levels during morning peaks and whenever there's a network outage.

The Director of Customer Operations asks:

1. **How are our call centers performing?** Speed of answer, handle time, first-call resolution (FCR), transfers, CSAT.
2. **Why are so many truck rolls finding nothing wrong?** How much do "No Fault Found" (NFF) visits cost, and where do they come from?
3. **Does proactive outage notification reduce calls?** Some 2025 outages sent customers a text/app alert; others didn't.
4. **Where should we staff and coach?** Which hours and which agent groups need help?

*Why this project fits you:* it mirrors contact-center supervision work (FCR, AHT, queue times, agent coaching) — you can speak to these metrics from real operational experience.

## 2. Datasets (`data/`)

| File | Rows | Grain | Key columns |
|---|---|---|---|
| `calls.csv` | 120,633 | 1 row per inbound call (2025) | call_start, customer_id, market, agent_id, call_reason, queue_wait_sec, handle_time_sec, transferred, resolved_first_contact, truck_roll_created, csat_score |
| `agents.csv` | 400 | 1 row per agent | center, tenure_months, team_lead, hire_cohort |
| `outages.csv` | 420 | 1 row per network outage | market, start_time, end_time, cause, customers_affected, proactive_notification_sent |
| `truck_rolls.csv` | 13,243 | 1 row per technician job | call_id, job_type, tech_id, resolution_code, no_fault_found, missed_appointment, repeat_truck_roll_30d, job_cost_usd |

Joins: `calls.agent_id → agents`, `truck_rolls.call_id → calls`, `calls (market + time window) → outages`. `customer_id` matches Project 1, so you can link both projects.

## 3. Tools
SQL (window functions, time-window joins) → Excel or Python for the cost model → Power BI → GitHub.

## 4. End-to-end steps

**Step 1 — Load & validate (SQL §1).** Row counts, date ranges, orphan truck rolls.

**Step 2 — Contact-center KPI baseline (SQL §2).** ASA, AHT, FCR, transfer rate, CSAT top-2-box, truck-roll rate.

**Step 3 — Call drivers (SQL §3).** Volume, AHT and FCR by call reason → a Pareto chart.

**Step 4 — Repeat callers (SQL §4).** Use `LAG()` to find customers calling back about the same issue within 7 days.

**Step 5 — Agent tenure impact (SQL §5).** Compare New (<6 months), Developing and Experienced agents; build an agent leaderboard ranked within each center for team-lead coaching.

**Step 6 — Staffing (SQL §6).** Calls and wait time by hour → identify when service level breaks.

**Step 7 — Outage analysis (SQL §7).** Time-window join of "No Internet" calls to outages; compute **calls per 1,000 affected customers** with vs. without proactive notification.

**Step 8 — Truck roll cost model (SQL §8).** NFF rate, NFF cost, repeat rolls, and NFF by call reason × agent cohort. Build a simple savings scenario in Excel: *"If remote troubleshooting cuts NFF rolls by 25%, we save $X."*

**Step 9 — Power BI dashboard (4 pages).**
- *Care Overview:* KPI cards, calls by reason Pareto, CSAT trend, hourly wait heatmap (hour × weekday).
- *Agent Performance:* FCR/AHT/transfer by cohort and center, drill-through to agent.
- *Outage Impact:* outage map/timeline, calls per 1K affected — notified vs. not.
- *Field Ops:* truck rolls, NFF %, NFF $ by reason, resolution codes, repeat-roll rate.

**Step 10 — Recommendations deck** (5–6 slides) + GitHub repo.

## 5. What you should find (answer key)

| Finding | Result in this data |
|---|---|
| Baseline KPIs | ~120.6K calls · ASA ≈ 3.5 min · AHT ≈ 10.3 min · FCR ≈ 72% · transfers ≈ 15% · CSAT top-2-box ≈ 65% |
| #1 call driver | "No Internet" (~38% of calls), inflated by outages |
| Morning peak | Avg wait jumps from ~3 min to **~5.4 min between 9–11 AM** |
| New agents (<6 mo) vs Experienced | FCR **52.5% vs 73%**, AHT **13.2 vs 10.1 min**, truck-roll rate **18.3% vs 10.5%** |
| Truck rolls | 13.2K rolls costing ~$1.94M; **NFF ≈ 34.5% = ~$671K** |
| NFF hotspot | "WiFi Help" calls → **56% NFF** (inside-WiFi / education issues a phone or app fix could solve) |
| Repeat rolls | 22% after an NFF visit vs 9% after a real fix |
| Proactive outage alerts | **~2.6 vs ~9.1 calls per 1K affected customers → ~70% fewer calls** |

**Recommended story:**
1. Make proactive outage notification standard for every outage — it's the cheapest call-deflection lever.
2. Add a mandatory remote WiFi troubleshooting step (app diagnostics / router reboot script) before booking a truck for WiFi calls; a 25% NFF reduction saves **~$168K/yr** on this sample.
3. Give new agents a tech-support "nesting" period with team-lead side-by-sides; they create nearly 2× the truck rolls.
4. Shift breaks and add part-time coverage for the 9–11 AM peak.

## 6. Resume bullets (edit numbers to match your final results)
- Analyzed 120K+ customer care calls, 13K technician visits and 420 network outages with SQL and Power BI to identify drivers of avoidable field cost and call volume.
- Quantified ~$670K in "No Fault Found" truck-roll cost and recommended remote WiFi troubleshooting projected to save ~$168K annually.
- Showed proactive outage notifications reduced outage call volume ~70%, and that new-hire agents generated nearly 2× the truck-roll rate, informing staffing and coaching plans.

## 7. 30-second interview pitch
"My second project looks at care and field operations. I joined call, agent, outage and technician data in SQL — including a time-window join to tie calls to outages — and found a third of truck rolls found no fault, mostly from in-home WiFi calls. I sized the savings from adding remote troubleshooting, showed proactive outage alerts cut calls by about 70%, and tied new-agent tenure to FCR and truck-roll rate. As a supervisor, I've managed these exact metrics, so I framed the recommendations the way an operations leader would act on them."
