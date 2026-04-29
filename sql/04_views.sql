CREATE OR REPLACE VIEW user_funnel_summary AS
WITH stages AS (
    SELECT 1 AS stage_order, 'signed_up' AS funnel_stage, user_id FROM users WHERE user_type = 'signed_up'
    UNION ALL SELECT 2, 'onboarding_completed', user_id FROM app_events WHERE event_name = 'onboarding_completed'
    UNION ALL SELECT 3, 'question_submitted', user_id FROM app_events WHERE event_name = 'question_submitted'
    UNION ALL SELECT 4, 'tutor_connected', user_id FROM app_events WHERE event_name = 'tutor_connected'
    UNION ALL SELECT 5, 'session_completed', user_id FROM sessions WHERE session_status = 'completed'
    UNION ALL SELECT 6, 'repeat_session', user_id FROM sessions GROUP BY user_id HAVING COUNT(*) >= 2
    UNION ALL SELECT 7, 'payment_completed', user_id FROM payments WHERE payment_status = 'completed'
),
stage_counts AS (
    SELECT stage_order, funnel_stage, COUNT(DISTINCT user_id) AS user_count
    FROM stages
    GROUP BY stage_order, funnel_stage
)
SELECT
    stage_order,
    funnel_stage,
    user_count,
    ROUND(100.0 * user_count / NULLIF(LAG(user_count) OVER (ORDER BY stage_order), 0), 2) AS conversion_from_previous_stage,
    ROUND(100.0 * user_count / NULLIF(FIRST_VALUE(user_count) OVER (ORDER BY stage_order), 0), 2) AS conversion_from_signup
FROM stage_counts;

CREATE OR REPLACE VIEW weekly_retention_summary AS
WITH cohorts AS (
    SELECT user_id, DATE_TRUNC('week', signup_date)::date AS signup_week
    FROM users
    WHERE user_type = 'signed_up'
),
activity AS (
    SELECT DISTINCT
        c.signup_week,
        c.user_id,
        ((e.event_time::date - c.signup_week) / 7)::int AS active_week
    FROM cohorts c
    JOIN app_events e ON c.user_id = e.user_id
    WHERE e.event_name IN ('app_opened', 'question_submitted', 'session_completed')
      AND ((e.event_time::date - c.signup_week) / 7)::int BETWEEN 0 AND 4
),
cohort_sizes AS (
    SELECT signup_week, COUNT(*) AS cohort_users
    FROM cohorts
    GROUP BY signup_week
)
SELECT
    cs.signup_week,
    cs.cohort_users,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE active_week = 0) / NULLIF(cs.cohort_users, 0), 2) AS week_0,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE active_week = 1) / NULLIF(cs.cohort_users, 0), 2) AS week_1,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE active_week = 2) / NULLIF(cs.cohort_users, 0), 2) AS week_2,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE active_week = 3) / NULLIF(cs.cohort_users, 0), 2) AS week_3,
    ROUND(100.0 * COUNT(DISTINCT user_id) FILTER (WHERE active_week = 4) / NULLIF(cs.cohort_users, 0), 2) AS week_4
FROM cohort_sizes cs
LEFT JOIN activity a ON cs.signup_week = a.signup_week
GROUP BY cs.signup_week, cs.cohort_users;

CREATE OR REPLACE VIEW subject_performance_summary AS
SELECT
    q.subject,
    COUNT(DISTINCT q.question_id) AS total_questions,
    COUNT(DISTINCT s.session_id) FILTER (WHERE s.session_status = 'completed') AS completed_sessions,
    ROUND(100.0 * COUNT(DISTINCT s.session_id) FILTER (WHERE s.session_status = 'completed')
        / NULLIF(COUNT(DISTINCT q.question_id), 0), 2) AS completion_rate,
    ROUND(AVG(f.rating), 2) AS avg_rating
FROM questions q
LEFT JOIN sessions s ON q.question_id = s.question_id
LEFT JOIN feedback f ON s.session_id = f.session_id
GROUP BY q.subject;

CREATE OR REPLACE VIEW payment_conversion_summary AS
SELECT
    u.acquisition_channel,
    COUNT(DISTINCT u.user_id) AS total_users,
    COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed') AS paid_users,
    ROUND(100.0 * COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed')
        / NULLIF(COUNT(DISTINCT u.user_id), 0), 2) AS payment_conversion_rate,
    ROUND(COALESCE(SUM(p.amount) FILTER (WHERE p.payment_status = 'completed'), 0), 2) AS total_revenue,
    ROUND(COALESCE(SUM(p.amount) FILTER (WHERE p.payment_status = 'completed'), 0)
        / NULLIF(COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed'), 0), 2) AS arppu
FROM users u
LEFT JOIN payments p ON u.user_id = p.user_id
GROUP BY u.acquisition_channel;

CREATE OR REPLACE VIEW wait_time_impact_summary AS
WITH bucketed AS (
    SELECT
        session_id,
        session_status,
        CASE
            WHEN wait_time_seconds BETWEEN 0 AND 60 THEN '0 to 60 sec'
            WHEN wait_time_seconds BETWEEN 61 AND 120 THEN '61 to 120 sec'
            WHEN wait_time_seconds BETWEEN 121 AND 180 THEN '121 to 180 sec'
            WHEN wait_time_seconds BETWEEN 181 AND 300 THEN '181 to 300 sec'
            ELSE '300+ sec'
        END AS wait_time_bucket
    FROM sessions
)
SELECT
    wait_time_bucket,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE session_status = 'completed') AS completed_sessions,
    COUNT(*) FILTER (WHERE session_status <> 'completed') AS abandoned_sessions,
    ROUND(100.0 * COUNT(*) FILTER (WHERE session_status = 'completed') / NULLIF(COUNT(*), 0), 2) AS completion_rate,
    ROUND(100.0 * COUNT(*) FILTER (WHERE session_status <> 'completed') / NULLIF(COUNT(*), 0), 2) AS abandonment_rate,
    ROUND(AVG(f.rating), 2) AS avg_feedback_rating
FROM bucketed b
LEFT JOIN feedback f ON b.session_id = f.session_id
GROUP BY wait_time_bucket;
