# EdTech Product Funnel & Retention Analysis using PostgreSQL

A complete synthetic product analytics project that analyzes signup, activation, tutor connection, session completion, repeat usage, retention, and paid conversion for an EdTech doubt-solving app.

## Business Problem

Many EdTech users install or sign up but do not complete their first successful learning session. This project identifies where users drop off in the journey and recommends product actions to improve activation, retention, and monetization.

## Why This Project Matters

This project is designed for Associate Product Manager, Product Analyst, Business Analyst, and EdTech roles. It demonstrates how to translate a product journey into a database schema, generate realistic behavioral data, write SQL analysis, define KPIs, and turn findings into product recommendations.

## Dataset

All data is synthetic and generated locally. No real company, student, tutor, user, or payment data is used.

Generated dataset size:

| Table | Rows |
|---|---:|
| users | 5,000 |
| app_events | 40,000 |
| questions | 12,000 |
| tutors | 500 |
| sessions | 8,000 |
| payments | 1,500 |
| feedback | 5,000 |

The generator includes realistic product behavior:

- Not every installed user signs up.
- Not every signed-up user asks a question.
- Not every question gets a tutor connection.
- Longer wait time increases abandonment.
- Completed sessions increase repeat usage probability.
- Higher ratings increase payment probability.
- Math and Physics have higher demand.
- Payment conversion varies by acquisition channel.

## Database Schema Summary

Core tables:

- `users`: signup, city, grade, acquisition channel, device, and activity status.
- `app_events`: event stream for install, signup, onboarding, question, session, and payment events.
- `questions`: student doubts by subject, difficulty, status, and source.
- `tutors`: tutor supply by subject, city, rating, and active status.
- `sessions`: tutor connection, wait time, duration, and completion status.
- `payments`: plan, amount, method, and payment status.
- `feedback`: session rating and qualitative feedback.

## KPIs Tracked

- Activation Rate
- Tutor Connection Rate
- Session Completion Rate
- Repeat Usage Rate
- Payment Conversion Rate
- Average Wait Time
- Average Session Rating
- Revenue
- ARPPU
- Churn Rate

## SQL Concepts Used

- Joins
- CTEs
- Window functions
- Aggregations
- Conditional aggregation with `FILTER`
- Cohort analysis
- Funnel analysis
- JSONB columns
- Views
- Indexes
- Date and time analysis

## Dashboard Screenshots

Add screenshots after running the Streamlit app:

- Executive Summary
- Funnel Analysis
- Retention Cohort Table
- Subject Performance
- Wait Time Impact
- Payment Conversion
- Product Recommendations

## Key Insights

Example insights supported by the project analysis:

- Activation is lower than signup, showing a clear gap between account creation and first question.
- Math and Physics create the largest demand and should be monitored for tutor supply constraints.
- Sessions with wait time above 180 seconds show materially lower completion.
- Users with completed first sessions are more likely to return.
- Referral and school partnership users tend to convert better than broad paid social traffic.

## Product Recommendations

- Reduce tutor wait time below 120 seconds for Math and Physics doubts.
- Improve onboarding for low-activation acquisition channels.
- Trigger nudges for users who asked one question but did not complete a session.
- Prioritize tutor supply for subjects with high demand and low completion.
- Show paid plan offers after a successful first session instead of before value is delivered.

## How to Run Locally

1. Start PostgreSQL:

```bash
docker compose up -d
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create local environment file:

```bash
cp .env.example .env
```

4. Generate synthetic data:

```bash
python scripts/generate_synthetic_data.py
```

5. Load data into PostgreSQL:

```bash
python scripts/load_data.py
```

6. Run the dashboard:

```bash
streamlit run dashboard/app.py
```

## Resume Bullet Points

- Built a PostgreSQL product analytics project simulating an EdTech doubt-solving app with 72,000+ synthetic records across users, events, questions, sessions, payments, and feedback.
- Designed SQL funnel, cohort retention, churn, subject demand, wait-time impact, and payment conversion analyses using CTEs, joins, window functions, views, and indexes.
- Developed a Streamlit dashboard to track activation, session completion, repeat usage, revenue, ARPPU, and acquisition-channel conversion.
- Converted behavioral data insights into PM recommendations for onboarding, tutor supply, re-engagement, wait-time reduction, and monetization timing.

