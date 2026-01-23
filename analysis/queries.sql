-- ============================================================================
-- Claude Thinking Budget Audit - Analysis Queries
-- ============================================================================
-- Run these against ~/.claude-audit/thinking_audit.db
-- Usage: sqlite3 ~/.claude-audit/thinking_audit.db < queries.sql
-- ============================================================================

-- 1. DAILY THINKING UTILIZATION SUMMARY
-- Shows average thinking utilization per day
SELECT 
    date(timestamp) as day,
    ROUND(AVG(thinking_utilization), 2) as avg_utilization_pct,
    ROUND(AVG(thinking_budget_requested), 0) as avg_budget_requested,
    ROUND(AVG(thinking_tokens_used), 0) as avg_tokens_used,
    COUNT(*) as sample_count
FROM audit_samples 
WHERE thinking_enabled = 1
GROUP BY day
ORDER BY day DESC
LIMIT 14;

-- 2. THINKING UTILIZATION BY MODEL
-- Compare utilization across different Claude models
SELECT 
    model_requested,
    ROUND(AVG(thinking_utilization), 2) as avg_utilization_pct,
    ROUND(AVG(thinking_budget_requested), 0) as avg_budget,
    COUNT(*) as samples
FROM audit_samples 
WHERE thinking_enabled = 1
GROUP BY model_requested
ORDER BY avg_utilization_pct DESC;

-- 3. THINKING UTILIZATION BY BACKEND
-- Check if throttling differs by hardware
SELECT 
    classified_backend,
    ROUND(AVG(thinking_utilization), 2) as avg_utilization_pct,
    ROUND(AVG(itt_mean_ms), 2) as avg_itt_ms,
    ROUND(AVG(variance_coef), 3) as avg_variance,
    COUNT(*) as samples
FROM audit_samples 
WHERE thinking_enabled = 1
GROUP BY classified_backend
ORDER BY samples DESC;

-- 4. UTILIZATION DISTRIBUTION (HISTOGRAM)
-- Shows how many requests fall into each utilization tier
SELECT 
    CASE 
        WHEN thinking_utilization >= 50 THEN '50-100% (FULL)'
        WHEN thinking_utilization >= 30 THEN '30-50% (GOOD)'
        WHEN thinking_utilization >= 20 THEN '20-30% (MEDIUM)'
        WHEN thinking_utilization >= 10 THEN '10-20% (LOW)'
        ELSE '0-10% (THROTTLED)'
    END as utilization_tier,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM audit_samples WHERE thinking_enabled = 1), 1) as percentage
FROM audit_samples 
WHERE thinking_enabled = 1
GROUP BY utilization_tier
ORDER BY 
    CASE utilization_tier
        WHEN '50-100% (FULL)' THEN 1
        WHEN '30-50% (GOOD)' THEN 2
        WHEN '20-30% (MEDIUM)' THEN 3
        WHEN '10-20% (LOW)' THEN 4
        ELSE 5
    END;

-- 5. MODEL ROUTING VERIFICATION
-- Check if requested model matches received model
SELECT 
    model_requested,
    model_response,
    model_match,
    COUNT(*) as count
FROM audit_samples 
GROUP BY model_requested, model_response, model_match
ORDER BY count DESC;

-- 6. ITT FINGERPRINT BASELINES
-- Establish timing baselines per model
SELECT 
    model_response,
    ROUND(AVG(itt_mean_ms), 2) as avg_itt_ms,
    ROUND(AVG(itt_std_ms), 2) as avg_std_ms,
    ROUND(AVG(variance_coef), 3) as avg_variance,
    ROUND(AVG(tokens_per_sec), 1) as avg_tps,
    COUNT(*) as samples
FROM audit_samples 
GROUP BY model_response
ORDER BY samples DESC;

-- 7. EVIDENCE SUMMARY FOR COMPLAINTS
-- Generates summary suitable for FTC/legal complaints
SELECT 
    'TOTAL SAMPLES' as metric, COUNT(*) as value FROM audit_samples
UNION ALL
SELECT 
    'AVG BUDGET REQUESTED', ROUND(AVG(thinking_budget_requested), 0) 
FROM audit_samples WHERE thinking_enabled = 1
UNION ALL
SELECT 
    'AVG TOKENS DELIVERED', ROUND(AVG(thinking_tokens_used), 0) 
FROM audit_samples WHERE thinking_enabled = 1
UNION ALL
SELECT 
    'AVG UTILIZATION %', ROUND(AVG(thinking_utilization), 2) 
FROM audit_samples WHERE thinking_enabled = 1
UNION ALL
SELECT 
    'THROTTLED SAMPLES (<10%)', COUNT(*) 
FROM audit_samples WHERE thinking_enabled = 1 AND thinking_utilization < 10
UNION ALL
SELECT 
    '% THROTTLED', ROUND(
        (SELECT COUNT(*) FROM audit_samples WHERE thinking_enabled = 1 AND thinking_utilization < 10) * 100.0 /
        (SELECT COUNT(*) FROM audit_samples WHERE thinking_enabled = 1), 1
    );

-- 8. HOURLY PATTERN (Check for time-based throttling)
SELECT 
    strftime('%H', timestamp) as hour,
    ROUND(AVG(thinking_utilization), 2) as avg_utilization,
    COUNT(*) as samples
FROM audit_samples 
WHERE thinking_enabled = 1
GROUP BY hour
ORDER BY hour;

-- 9. WORST OFFENDERS (Lowest utilization samples)
SELECT 
    timestamp,
    model_requested,
    thinking_budget_requested,
    thinking_tokens_used,
    thinking_utilization,
    classified_backend
FROM audit_samples 
WHERE thinking_enabled = 1
ORDER BY thinking_utilization ASC
LIMIT 20;

-- 10. EXPORT FOR ANALYSIS (CSV-friendly)
-- .mode csv
-- .output thinking_audit_export.csv
SELECT 
    timestamp,
    model_requested,
    model_response,
    thinking_enabled,
    thinking_budget_requested,
    thinking_tokens_used,
    thinking_utilization,
    itt_mean_ms,
    variance_coef,
    classified_backend,
    tokens_per_sec
FROM audit_samples 
ORDER BY timestamp DESC;
