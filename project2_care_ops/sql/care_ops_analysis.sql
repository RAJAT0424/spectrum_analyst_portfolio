-- =====================================================================
-- PROJECT 2: Spectrum Customer Care & Field Operations
-- "Reducing repeat calls and avoidable truck rolls"
-- SQL (PostgreSQL syntax)
-- =====================================================================

-- ---------- STEP 1: DATA QUALITY ----------
SELECT COUNT(*) total_calls, COUNT(DISTINCT call_id) distinct_calls,
       MIN(call_start) first_call, MAX(call_start) last_call
FROM calls;

SELECT COUNT(*) AS rolls_without_call
FROM truck_rolls tr LEFT JOIN calls c USING (call_id)
WHERE c.call_id IS NULL;                       -- expect 0

-- ---------- STEP 2: CORE CONTACT-CENTER KPIs ----------
SELECT
  COUNT(*)                                                   AS calls,
  ROUND(AVG(queue_wait_sec))                                 AS avg_speed_of_answer_sec,
  ROUND(AVG(handle_time_sec)/60.0,1)                         AS aht_min,
  ROUND(100*AVG(CASE WHEN resolved_first_contact THEN 1.0 ELSE 0 END),1) AS fcr_pct,
  ROUND(100*AVG(CASE WHEN transferred THEN 1.0 ELSE 0 END),1)            AS transfer_pct,
  ROUND(100*AVG(CASE WHEN csat_score >= 4 THEN 1.0 ELSE 0 END),1)        AS csat_top2box_pct,
  ROUND(100*AVG(CASE WHEN truck_roll_created THEN 1.0 ELSE 0 END),1)     AS truck_roll_rate_pct
FROM calls;

-- ---------- STEP 3: CALL DRIVERS ----------
SELECT call_reason, COUNT(*) calls,
       ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (),1) pct_of_volume,
       ROUND(AVG(handle_time_sec)/60.0,1) aht_min,
       ROUND(100*AVG(CASE WHEN resolved_first_contact THEN 1.0 ELSE 0 END),1) fcr_pct
FROM calls GROUP BY 1 ORDER BY 2 DESC;

-- ---------- STEP 4: REPEAT CALLERS (same customer, same reason, within 7 days) ----------
WITH ordered AS (
  SELECT customer_id, call_reason, CAST(call_start AS TIMESTAMP) ts,
         LAG(CAST(call_start AS TIMESTAMP)) OVER (PARTITION BY customer_id, call_reason ORDER BY call_start) prev_ts
  FROM calls)
SELECT call_reason,
       COUNT(*) FILTER (WHERE ts - prev_ts <= INTERVAL '7 days') AS repeat_calls,
       ROUND(100.0*COUNT(*) FILTER (WHERE ts - prev_ts <= INTERVAL '7 days')/COUNT(*),1) AS repeat_rate_pct
FROM ordered GROUP BY 1 ORDER BY 3 DESC;

-- ---------- STEP 5: AGENT TENURE IMPACT ----------
SELECT a.hire_cohort, COUNT(*) calls,
       ROUND(AVG(c.handle_time_sec)/60.0,1) aht_min,
       ROUND(100*AVG(CASE WHEN c.resolved_first_contact THEN 1.0 ELSE 0 END),1) fcr_pct,
       ROUND(100*AVG(CASE WHEN c.transferred THEN 1.0 ELSE 0 END),1) transfer_pct,
       ROUND(100*AVG(CASE WHEN c.truck_roll_created THEN 1.0 ELSE 0 END),1) truck_roll_pct,
       ROUND(AVG(c.csat_score),2) avg_csat
FROM calls c JOIN agents a USING (agent_id)
GROUP BY 1 ORDER BY 4;

-- Agent leaderboard (min 200 calls) - for team lead coaching
SELECT a.center, a.team_lead, c.agent_id, a.tenure_months, COUNT(*) calls,
       ROUND(100*AVG(CASE WHEN c.resolved_first_contact THEN 1.0 ELSE 0 END),1) fcr_pct,
       RANK() OVER (PARTITION BY a.center ORDER BY AVG(CASE WHEN c.resolved_first_contact THEN 1.0 ELSE 0 END) DESC) fcr_rank_in_center
FROM calls c JOIN agents a USING (agent_id)
GROUP BY 1,2,3,4 HAVING COUNT(*) >= 200
ORDER BY 1, 7;

-- ---------- STEP 6: STAFFING - VOLUME & WAIT BY HOUR ----------
SELECT EXTRACT(HOUR FROM CAST(call_start AS TIMESTAMP)) hr,
       COUNT(*) calls, ROUND(AVG(queue_wait_sec)) avg_wait_sec,
       ROUND(100*AVG(CASE WHEN queue_wait_sec > 300 THEN 1.0 ELSE 0 END),1) pct_wait_over_5min
FROM calls GROUP BY 1 ORDER BY 1;

-- ---------- STEP 7: OUTAGES -> CALL SPIKES (proactive notification test) ----------
SELECT o.outage_id, o.market, o.cause, o.customers_affected, o.proactive_notification_sent,
       COUNT(c.call_id) AS calls_during_outage,
       ROUND(1000.0*COUNT(c.call_id)/o.customers_affected,1) AS calls_per_1k_affected
FROM outages o
LEFT JOIN calls c
  ON c.market = o.market
 AND c.call_reason = 'No Internet'
 AND CAST(c.call_start AS TIMESTAMP) BETWEEN CAST(o.start_time AS TIMESTAMP) AND CAST(o.end_time AS TIMESTAMP)
GROUP BY 1,2,3,4,5;
-- Then summarize the result above:
-- SELECT proactive_notification_sent, ROUND(AVG(calls_per_1k_affected),1) FROM <above> GROUP BY 1;

-- ---------- STEP 8: TRUCK ROLLS - AVOIDABLE COST ----------
SELECT
  COUNT(*)                                                         AS truck_rolls,
  ROUND(100*AVG(CASE WHEN no_fault_found THEN 1.0 ELSE 0 END),1)   AS nff_rate_pct,
  ROUND(SUM(CASE WHEN no_fault_found THEN job_cost_usd ELSE 0 END)) AS nff_cost_usd,
  ROUND(100*AVG(CASE WHEN repeat_truck_roll_30d THEN 1.0 ELSE 0 END),1) AS repeat_roll_pct,
  ROUND(100*AVG(CASE WHEN missed_appointment THEN 1.0 ELSE 0 END),1)    AS missed_appt_pct
FROM truck_rolls;

-- NFF by originating call reason and agent cohort (where to add remote troubleshooting)
SELECT c.call_reason, a.hire_cohort, COUNT(*) rolls,
       ROUND(100*AVG(CASE WHEN tr.no_fault_found THEN 1.0 ELSE 0 END),1) nff_pct,
       ROUND(SUM(CASE WHEN tr.no_fault_found THEN tr.job_cost_usd ELSE 0 END)) nff_cost
FROM truck_rolls tr
JOIN calls c USING (call_id)
JOIN agents a ON a.agent_id = c.agent_id
GROUP BY 1,2 ORDER BY 5 DESC;

SELECT resolution_code, COUNT(*) n, ROUND(SUM(job_cost_usd)) cost
FROM truck_rolls GROUP BY 1 ORDER BY 2 DESC;
