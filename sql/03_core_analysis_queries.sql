-- 1. User acquisition by channel
SELECT
    acquisition_channel,
    COUNT(*) AS total_users,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) AS percentage_share
FROM users
GROUP BY acquisition_channel
ORDER BY total_users DESC;

-- 2. Signup to first question activation funnel
WITH signed_up AS (
    SELECT user_id FROM users WHERE user_type = 'signed_up'
),
question_users AS (
    SELECT DISTINCT user_id FROM questions
)
SELECT
    COUNT(s.user_id) AS total_signed_up_users,
    COUNT(q.user_id) AS users_who_asked_question,
    ROUND(100.0 * COUNT(q.user_id) / NULLIF(COUNT(s.user_id), 0), 2) AS activation_rate
FROM signed_up s
LEFT JOIN question_users q ON s.user_id = q.user_id;

-- 3. Full funnel analysis
WITH stages AS (
    SELECT 1 AS stage_order, 'signed_up' AS funnel_stage, user_id FROM users WHERE user_type = 'signed_up'
    UNION ALL
    SELECT 2, 'onboarding_completed', user_id FROM app_events WHERE event_name = 'onboarding_completed'
    UNION ALL
    SELECT 3, 'question_submitted', user_id FROM app_events WHERE event_name = 'question_submitted'
    UNION ALL
    SELECT 4, 'tutor_connected', user_id FROM app_events WHERE event_name = 'tutor_connected'
    UNION ALL
    SELECT 5, 'session_completed', user_id FROM sessions WHERE session_status = 'completed'
    UNION ALL
    SELECT 6, 'repeat_session', user_id FROM sessions GROUP BY user_id HAVING COUNT(*) >= 2
    UNION ALL
    SELECT 7, 'payment_completed', user_id FROM payments WHERE payment_status = 'completed'
),
stage_counts AS (
    SELECT stage_order, funnel_stage, COUNT(DISTINCT user_id) AS user_count
    FROM stages
    GROUP BY stage_order, funnel_stage
),
with_baseline AS (
    SELECT
        stage_order,
        funnel_stage,
        user_count,
        LAG(user_count) OVER (ORDER BY stage_order) AS previous_stage_users,
        FIRST_VALUE(user_count) OVER (ORDER BY stage_order) AS signup_users
    FROM stage_counts
)
SELECT
    funnel_stage,
    user_count,
    ROUND(100.0 * user_count / NULLIF(previous_stage_users, 0), 2) AS conversion_from_previous_stage,
    ROUND(100.0 * user_count / NULLIF(signup_users, 0), 2) AS conversion_from_signup
FROM with_baseline
ORDER BY stage_order;

-- 4. Subject-wise demand analysis
SELECT
    q.subject,
    COUNT(DISTINCT q.question_id) AS total_questions,
    COUNT(DISTINCT CASE WHEN s.session_status = 'completed' THEN s.session_id END) AS completed_sessions,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN s.session_status = 'completed' THEN s.session_id END)
        / NULLIF(COUNT(DISTINCT q.question_id), 0), 2) AS completion_rate,
    ROUND(AVG(f.rating), 2) AS avg_rating
FROM questions q
LEFT JOIN sessions s ON q.question_id = s.question_id
LEFT JOIN feedback f ON s.session_id = f.session_id
GROUP BY q.subject
ORDER BY total_questions DESC;

-- 5. Wait time impact analysis
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
    b.wait_time_bucket,
    COUNT(*) AS total_sessions,
    COUNT(*) FILTER (WHERE b.session_status = 'completed') AS completed_sessions,
    COUNT(*) FILTER (WHERE b.session_status <> 'completed') AS abandoned_sessions,
    ROUND(100.0 * COUNT(*) FILTER (WHERE b.session_status = 'completed') / NULLIF(COUNT(*), 0), 2) AS completion_rate,
    ROUND(AVG(f.rating), 2) AS avg_feedback_rating
FROM bucketed b
LEFT JOIN feedback f ON b.session_id = f.session_id
GROUP BY b.wait_time_bucket
ORDER BY MIN(CASE b.wait_time_bucket
    WHEN '0 to 60 sec' THEN 1
    WHEN '61 to 120 sec' THEN 2
    WHEN '121 to 180 sec' THEN 3
    WHEN '181 to 300 sec' THEN 4
    ELSE 5
END);

-- 6. Retention cohort analysis by signup week
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
GROUP BY cs.signup_week, cs.cohort_users
ORDER BY cs.signup_week;

-- 7. Churn analysis
WITH user_session_counts AS (
    SELECT user_id, COUNT(*) AS total_sessions, COUNT(*) FILTER (WHERE session_status = 'completed') AS completed_sessions
    FROM sessions
    GROUP BY user_id
)
SELECT 'signed_up_never_asked_question' AS churn_segment, COUNT(*) AS users
FROM users u
LEFT JOIN questions q ON u.user_id = q.user_id
WHERE u.user_type = 'signed_up' AND q.question_id IS NULL
UNION ALL
SELECT 'asked_one_question_never_completed_session', COUNT(*)
FROM (
    SELECT u.user_id
    FROM users u
    JOIN questions q ON u.user_id = q.user_id
    LEFT JOIN user_session_counts usc ON u.user_id = usc.user_id
    GROUP BY u.user_id, COALESCE(usc.completed_sessions, 0)
    HAVING COUNT(q.question_id) = 1 AND COALESCE(usc.completed_sessions, 0) = 0
) one_question_churn
UNION ALL
SELECT 'completed_one_session_never_returned', COUNT(*)
FROM user_session_counts
WHERE completed_sessions = 1
UNION ALL
SELECT 'payment_page_viewed_did_not_pay', COUNT(DISTINCT e.user_id)
FROM app_events e
LEFT JOIN payments p ON e.user_id = p.user_id AND p.payment_status = 'completed'
WHERE e.event_name = 'payment_page_viewed' AND p.payment_id IS NULL;

-- 8. Payment conversion analysis
SELECT
    u.acquisition_channel,
    COUNT(DISTINCT u.user_id) AS total_users,
    COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed') AS paid_users,
    ROUND(100.0 * COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed')
        / NULLIF(COUNT(DISTINCT u.user_id), 0), 2) AS payment_conversion_rate,
    ROUND(COALESCE(SUM(p.amount) FILTER (WHERE p.payment_status = 'completed'), 0), 2) AS total_revenue,
    ROUND(COALESCE(SUM(p.amount) FILTER (WHERE p.payment_status = 'completed'), 0)
        / NULLIF(COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed'), 0), 2) AS avg_revenue_per_paid_user
FROM users u
LEFT JOIN payments p ON u.user_id = p.user_id
GROUP BY u.acquisition_channel
ORDER BY payment_conversion_rate DESC;

-- 9. Grade-wise product usage
SELECT
    u.grade,
    COUNT(DISTINCT u.user_id) AS total_users,
    COUNT(DISTINCT q.question_id) AS total_questions,
    COUNT(DISTINCT s.session_id) FILTER (WHERE s.session_status = 'completed') AS completed_sessions,
    COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed') AS paid_users,
    ROUND(100.0 * COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed')
        / NULLIF(COUNT(DISTINCT u.user_id), 0), 2) AS conversion_rate
FROM users u
LEFT JOIN questions q ON u.user_id = q.user_id
LEFT JOIN sessions s ON u.user_id = s.user_id
LEFT JOIN payments p ON u.user_id = p.user_id
GROUP BY u.grade
ORDER BY u.grade;

-- 10a. Top opportunity: highest drop-off stage
WITH funnel AS (
    SELECT * FROM (
        SELECT 1 AS stage_order, 'signed_up' AS stage, COUNT(DISTINCT user_id) AS users FROM users WHERE user_type = 'signed_up'
        UNION ALL SELECT 2, 'onboarding_completed', COUNT(DISTINCT user_id) FROM app_events WHERE event_name = 'onboarding_completed'
        UNION ALL SELECT 3, 'question_submitted', COUNT(DISTINCT user_id) FROM app_events WHERE event_name = 'question_submitted'
        UNION ALL SELECT 4, 'tutor_connected', COUNT(DISTINCT user_id) FROM app_events WHERE event_name = 'tutor_connected'
        UNION ALL SELECT 5, 'session_completed', COUNT(DISTINCT user_id) FROM sessions WHERE session_status = 'completed'
        UNION ALL SELECT 6, 'repeat_session', COUNT(*) FROM (SELECT user_id FROM sessions GROUP BY user_id HAVING COUNT(*) >= 2) x
        UNION ALL SELECT 7, 'payment_completed', COUNT(DISTINCT user_id) FROM payments WHERE payment_status = 'completed'
    ) x
),
dropoffs AS (
    SELECT stage, LAG(stage) OVER (ORDER BY stage_order) AS previous_stage, LAG(users) OVER (ORDER BY stage_order) - users AS dropped_users
    FROM funnel
)
SELECT previous_stage || ' to ' || stage AS dropoff_point, dropped_users
FROM dropoffs
WHERE previous_stage IS NOT NULL
ORDER BY dropped_users DESC
LIMIT 1;

-- 10b. Top opportunity: worst performing acquisition channel by payment conversion
SELECT
    u.acquisition_channel,
    COUNT(DISTINCT u.user_id) AS users,
    ROUND(100.0 * COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed')
        / NULLIF(COUNT(DISTINCT u.user_id), 0), 2) AS payment_conversion_rate
FROM users u
LEFT JOIN payments p ON u.user_id = p.user_id
GROUP BY u.acquisition_channel
HAVING COUNT(DISTINCT u.user_id) >= 100
ORDER BY payment_conversion_rate ASC
LIMIT 1;

-- 10c. Top opportunity: subject with high demand but low completion
SELECT
    q.subject,
    COUNT(DISTINCT q.question_id) AS total_questions,
    ROUND(100.0 * COUNT(DISTINCT s.session_id) FILTER (WHERE s.session_status = 'completed')
        / NULLIF(COUNT(DISTINCT q.question_id), 0), 2) AS completion_rate
FROM questions q
LEFT JOIN sessions s ON q.question_id = s.question_id
GROUP BY q.subject
ORDER BY total_questions DESC, completion_rate ASC
LIMIT 1;

-- 10d. Top opportunity: wait time bucket with lowest completion
WITH bucketed AS (
    SELECT
        CASE
            WHEN wait_time_seconds BETWEEN 0 AND 60 THEN '0 to 60 sec'
            WHEN wait_time_seconds BETWEEN 61 AND 120 THEN '61 to 120 sec'
            WHEN wait_time_seconds BETWEEN 121 AND 180 THEN '121 to 180 sec'
            WHEN wait_time_seconds BETWEEN 181 AND 300 THEN '181 to 300 sec'
            ELSE '300+ sec'
        END AS wait_time_bucket,
        session_status
    FROM sessions
)
SELECT
    wait_time_bucket,
    ROUND(100.0 * COUNT(*) FILTER (WHERE session_status = 'completed') / NULLIF(COUNT(*), 0), 2) AS completion_rate
FROM bucketed
GROUP BY wait_time_bucket
ORDER BY completion_rate ASC
LIMIT 1;

-- 10e. Top opportunity: high payment intent but low conversion segment
SELECT
    u.acquisition_channel,
    COUNT(DISTINCT e.user_id) AS payment_intent_users,
    COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed') AS paid_users,
    ROUND(100.0 * COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed')
        / NULLIF(COUNT(DISTINCT e.user_id), 0), 2) AS intent_to_payment_rate
FROM app_events e
JOIN users u ON e.user_id = u.user_id
LEFT JOIN payments p ON e.user_id = p.user_id
WHERE e.event_name = 'payment_page_viewed'
GROUP BY u.acquisition_channel
HAVING COUNT(DISTINCT e.user_id) >= 50
ORDER BY intent_to_payment_rate ASC
LIMIT 1;
