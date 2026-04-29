from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[1]


@st.cache_resource
def get_engine():
    load_dotenv(BASE_DIR / ".env")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "edtech_analytics")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}")


@st.cache_data(ttl=300)
def query(sql: str) -> pd.DataFrame:
    return pd.read_sql(text(sql), get_engine())


def metric_value(value, suffix: str = "") -> str:
    if pd.isna(value):
        return "0"
    if isinstance(value, float):
        return f"{value:,.2f}{suffix}"
    return f"{value:,}{suffix}"


st.set_page_config(page_title="EdTech Product Funnel Analytics", layout="wide")
st.title("EdTech Product Funnel & Retention Analysis")
st.caption("Synthetic PostgreSQL product analytics project for funnel, retention, and monetization analysis.")

summary = query(
    """
    WITH base AS (
        SELECT
            COUNT(DISTINCT u.user_id) AS total_users,
            COUNT(DISTINCT q.user_id) AS activated_users,
            COUNT(DISTINCT s.session_id) FILTER (WHERE s.session_status = 'completed') AS completed_sessions,
            COUNT(DISTINCT s.session_id) AS total_sessions,
            COUNT(DISTINCT repeat_users.user_id) AS repeat_users,
            COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed') AS paid_users,
            COALESCE(SUM(p.amount) FILTER (WHERE p.payment_status = 'completed'), 0) AS total_revenue
        FROM users u
        LEFT JOIN questions q ON u.user_id = q.user_id
        LEFT JOIN sessions s ON u.user_id = s.user_id
        LEFT JOIN payments p ON u.user_id = p.user_id
        LEFT JOIN (
            SELECT user_id
            FROM sessions
            GROUP BY user_id
            HAVING COUNT(*) >= 2
        ) repeat_users ON u.user_id = repeat_users.user_id
        WHERE u.user_type = 'signed_up'
    )
    SELECT
        total_users,
        ROUND(100.0 * activated_users / NULLIF(total_users, 0), 2) AS activation_rate,
        ROUND(100.0 * completed_sessions / NULLIF(total_sessions, 0), 2) AS session_completion_rate,
        ROUND(100.0 * repeat_users / NULLIF(activated_users, 0), 2) AS repeat_usage_rate,
        ROUND(100.0 * paid_users / NULLIF(total_users, 0), 2) AS paid_conversion_rate,
        ROUND(total_revenue, 2) AS total_revenue
    FROM base;
    """
)

st.header("Executive Summary")
cols = st.columns(6)
if not summary.empty:
    row = summary.iloc[0]
    cols[0].metric("Total Users", metric_value(int(row["total_users"])))
    cols[1].metric("Activation Rate", metric_value(float(row["activation_rate"]), "%"))
    cols[2].metric("Completion Rate", metric_value(float(row["session_completion_rate"]), "%"))
    cols[3].metric("Repeat Usage", metric_value(float(row["repeat_usage_rate"]), "%"))
    cols[4].metric("Paid Conversion", metric_value(float(row["paid_conversion_rate"]), "%"))
    cols[5].metric("Revenue", f"INR {row['total_revenue']:,.0f}")

st.header("Funnel Analysis")
funnel = query("SELECT funnel_stage, user_count, conversion_from_previous_stage, conversion_from_signup FROM user_funnel_summary ORDER BY stage_order;")
c1, c2 = st.columns([1.3, 1])
with c1:
    st.plotly_chart(px.funnel(funnel, x="user_count", y="funnel_stage", title="User Journey Funnel"), use_container_width=True)
with c2:
    st.dataframe(funnel, use_container_width=True, hide_index=True)

st.header("Retention Analysis")
retention = query("SELECT * FROM weekly_retention_summary ORDER BY signup_week;")
st.dataframe(retention, use_container_width=True, hide_index=True)

st.header("Subject Performance")
subject = query("SELECT * FROM subject_performance_summary ORDER BY total_questions DESC;")
c1, c2, c3 = st.columns(3)
with c1:
    st.plotly_chart(px.bar(subject, x="subject", y="total_questions", title="Questions by Subject"), use_container_width=True)
with c2:
    st.plotly_chart(px.bar(subject, x="subject", y="completion_rate", title="Completion Rate by Subject"), use_container_width=True)
with c3:
    st.plotly_chart(px.bar(subject, x="subject", y="avg_rating", title="Average Rating by Subject"), use_container_width=True)
st.dataframe(subject, use_container_width=True, hide_index=True)

st.header("Wait Time Impact")
wait_time = query(
    """
    SELECT *
    FROM wait_time_impact_summary
    ORDER BY CASE wait_time_bucket
        WHEN '0 to 60 sec' THEN 1
        WHEN '61 to 120 sec' THEN 2
        WHEN '121 to 180 sec' THEN 3
        WHEN '181 to 300 sec' THEN 4
        ELSE 5
    END;
    """
)
c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(px.line(wait_time, x="wait_time_bucket", y="completion_rate", markers=True, title="Completion Rate by Wait Time"), use_container_width=True)
with c2:
    st.plotly_chart(px.line(wait_time, x="wait_time_bucket", y="abandonment_rate", markers=True, title="Abandonment Rate by Wait Time"), use_container_width=True)
st.dataframe(wait_time, use_container_width=True, hide_index=True)

st.header("Payment Conversion")
payment = query("SELECT * FROM payment_conversion_summary ORDER BY payment_conversion_rate DESC;")
plan_revenue = query(
    """
    SELECT plan_type, ROUND(SUM(amount), 2) AS revenue
    FROM payments
    WHERE payment_status = 'completed'
    GROUP BY plan_type
    ORDER BY revenue DESC;
    """
)
arppu = query(
    """
    SELECT ROUND(SUM(amount) / NULLIF(COUNT(DISTINCT user_id), 0), 2) AS arppu
    FROM payments
    WHERE payment_status = 'completed';
    """
)
c1, c2, c3 = st.columns([1.2, 1.2, 0.8])
with c1:
    st.plotly_chart(px.bar(payment, x="acquisition_channel", y="payment_conversion_rate", title="Paid Conversion by Channel"), use_container_width=True)
with c2:
    st.plotly_chart(px.pie(plan_revenue, names="plan_type", values="revenue", title="Revenue by Plan Type"), use_container_width=True)
with c3:
    st.metric("ARPPU", f"INR {arppu.iloc[0]['arppu']:,.0f}")
st.dataframe(payment, use_container_width=True, hide_index=True)

st.header("Product Recommendations")
recommendations = [
    "Reduce tutor wait time below 120 seconds for Math and Physics doubts because completion drops as wait time rises.",
    "Improve onboarding for lower-activation paid social users before optimizing payment prompts.",
    "Trigger re-engagement nudges for users who submitted one question but did not complete a session.",
    "Prioritize tutor supply for high-demand subjects with lower completion rates.",
    "Show payment offers after a successful first completed session, when satisfaction and payment intent are higher.",
    "Use referral and school partnership channels as quality benchmarks for acquisition and retention.",
]
for recommendation in recommendations:
    st.write(f"- {recommendation}")

