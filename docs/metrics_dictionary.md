# Metrics Dictionary

| Metric | Definition | Formula |
|---|---|---|
| Activation Rate | Share of signed-up users who submit at least one question. | `users_who_asked_question / signed_up_users` |
| Tutor Connection Rate | Share of question submitters who connect with a tutor. | `users_with_tutor_connected / users_who_submitted_question` |
| Session Completion Rate | Share of sessions completed successfully. | `completed_sessions / total_sessions` |
| Repeat Usage Rate | Share of activated users with two or more sessions. | `users_with_2plus_sessions / activated_users` |
| Payment Conversion Rate | Share of users who completed payment. | `paid_users / total_users` |
| Average Wait Time | Average time between tutor search and session start. | `AVG(wait_time_seconds)` |
| Average Session Rating | Average feedback rating for completed sessions. | `AVG(rating)` |
| Revenue | Total completed payment amount. | `SUM(amount) WHERE payment_status = 'completed'` |
| ARPPU | Average revenue per paying user. | `revenue / paid_users` |
| Churn Rate | Share of users who fail to continue after a key milestone. | `churned_users / users_at_start_of_stage` |
| Onboarding Completion Rate | Share of signed-up users who complete onboarding. | `onboarding_completed_users / signed_up_users` |
| Payment Intent Rate | Share of users who viewed the payment page. | `payment_page_view_users / total_users` |
| Intent-to-Payment Rate | Share of payment page viewers who paid. | `paid_users / payment_page_view_users` |
| Subject Completion Rate | Share of questions in a subject that led to completed sessions. | `completed_sessions_by_subject / questions_by_subject` |
| Week N Retention | Share of a signup cohort active in week N. | `active_users_in_week_n / cohort_users` |

