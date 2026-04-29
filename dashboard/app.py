from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


BASE_DIR = Path(__file__).resolve().parents[1]


st.set_page_config(
    page_title="EdTech Product Analytics",
    layout="wide",
)


st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.6rem;
            padding-bottom: 2rem;
        }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05);
        }
        div[data-testid="stMetricLabel"] {
            color: #475569;
        }
        .insight-box {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 14px 16px;
            background: #f8fafc;
            min-height: 112px;
        }
        .insight-box strong {
            color: #0f172a;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def format_inr(value: float | int) -> str:
    if pd.isna(value):
        return "INR 0"
    return f"INR {value:,.0f}"


def style_chart(fig: go.Figure, height: int = 390) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=54, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#0f172a"),
        title_font=dict(size=17),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(gridcolor="#e5e7eb", title=None)
    return fig


def load_dashboard_data() -> dict[str, pd.DataFrame]:
    return {
        "summary": query(
            """
            WITH base AS (
                SELECT
                    COUNT(DISTINCT u.user_id) AS total_users,
                    COUNT(DISTINCT q.user_id) AS activated_users,
                    COUNT(DISTINCT s.session_id) AS total_sessions,
                    COUNT(DISTINCT s.session_id) FILTER (WHERE s.session_status = 'completed') AS completed_sessions,
                    COUNT(DISTINCT repeat_users.user_id) AS repeat_users,
                    COUNT(DISTINCT p.user_id) FILTER (WHERE p.payment_status = 'completed') AS paid_users,
                    COALESCE(SUM(p.amount) FILTER (WHERE p.payment_status = 'completed'), 0) AS total_revenue,
                    ROUND(AVG(s.wait_time_seconds), 0) AS avg_wait_seconds,
                    ROUND(AVG(f.rating), 2) AS avg_rating
                FROM users u
                LEFT JOIN questions q ON u.user_id = q.user_id
                LEFT JOIN sessions s ON u.user_id = s.user_id
                LEFT JOIN payments p ON u.user_id = p.user_id
                LEFT JOIN feedback f ON u.user_id = f.user_id
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
                activated_users,
                total_sessions,
                completed_sessions,
                ROUND(100.0 * activated_users / NULLIF(total_users, 0), 2) AS activation_rate,
                ROUND(100.0 * completed_sessions / NULLIF(total_sessions, 0), 2) AS session_completion_rate,
                ROUND(100.0 * repeat_users / NULLIF(activated_users, 0), 2) AS repeat_usage_rate,
                ROUND(100.0 * paid_users / NULLIF(total_users, 0), 2) AS paid_conversion_rate,
                ROUND(total_revenue, 2) AS total_revenue,
                ROUND(total_revenue / NULLIF(paid_users, 0), 2) AS arppu,
                avg_wait_seconds,
                avg_rating
            FROM base;
            """
        ),
        "funnel": query(
            """
            SELECT funnel_stage, user_count, conversion_from_previous_stage, conversion_from_signup
            FROM user_funnel_summary
            ORDER BY stage_order;
            """
        ),
        "retention": query("SELECT * FROM weekly_retention_summary ORDER BY signup_week;"),
        "subject": query("SELECT * FROM subject_performance_summary ORDER BY total_questions DESC;"),
        "wait_time": query(
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
        ),
        "payment": query("SELECT * FROM payment_conversion_summary ORDER BY payment_conversion_rate DESC;"),
        "plan_revenue": query(
            """
            SELECT plan_type, ROUND(SUM(amount), 2) AS revenue
            FROM payments
            WHERE payment_status = 'completed'
            GROUP BY plan_type
            ORDER BY revenue DESC;
            """
        ),
        "churn": query(
            """
            WITH user_session_counts AS (
                SELECT
                    user_id,
                    COUNT(*) AS total_sessions,
                    COUNT(*) FILTER (WHERE session_status = 'completed') AS completed_sessions
                FROM sessions
                GROUP BY user_id
            )
            SELECT 'Signed up, never asked question' AS churn_segment, COUNT(*) AS users
            FROM users u
            LEFT JOIN questions q ON u.user_id = q.user_id
            WHERE u.user_type = 'signed_up' AND q.question_id IS NULL
            UNION ALL
            SELECT 'Asked one question, no completed session', COUNT(*)
            FROM (
                SELECT u.user_id
                FROM users u
                JOIN questions q ON u.user_id = q.user_id
                LEFT JOIN user_session_counts usc ON u.user_id = usc.user_id
                GROUP BY u.user_id, COALESCE(usc.completed_sessions, 0)
                HAVING COUNT(q.question_id) = 1 AND COALESCE(usc.completed_sessions, 0) = 0
            ) one_question_churn
            UNION ALL
            SELECT 'Completed one session, never returned', COUNT(*)
            FROM user_session_counts
            WHERE completed_sessions = 1
            UNION ALL
            SELECT 'Viewed payment page, did not pay', COUNT(DISTINCT e.user_id)
            FROM app_events e
            LEFT JOIN payments p ON e.user_id = p.user_id AND p.payment_status = 'completed'
            WHERE e.event_name = 'payment_page_viewed' AND p.payment_id IS NULL;
            """
        ),
        "acquisition": query(
            """
            SELECT
                acquisition_channel,
                COUNT(*) AS users,
                COUNT(*) FILTER (WHERE user_type = 'signed_up') AS signed_up_users,
                ROUND(100.0 * COUNT(*) FILTER (WHERE user_type = 'signed_up') / NULLIF(COUNT(*), 0), 2) AS signup_rate
            FROM users
            GROUP BY acquisition_channel
            ORDER BY users DESC;
            """
        ),
        "event_trend": query(
            """
            SELECT
                DATE_TRUNC('week', event_time)::date AS event_week,
                COUNT(*) FILTER (WHERE event_name = 'app_opened') AS app_opens,
                COUNT(*) FILTER (WHERE event_name = 'question_submitted') AS questions_submitted,
                COUNT(*) FILTER (WHERE event_name = 'session_completed') AS sessions_completed,
                COUNT(*) FILTER (WHERE event_name = 'payment_completed') AS payments_completed
            FROM app_events
            GROUP BY event_week
            ORDER BY event_week;
            """
        ),
    }


def main() -> None:
    st.title("EdTech Product Analytics Dashboard")
    st.caption("Synthetic PostgreSQL dashboard for funnel, retention, tutor supply, session quality, and monetization analysis.")

    try:
        data = load_dashboard_data()
    except SQLAlchemyError as exc:
        st.error("Could not connect to PostgreSQL or query the analytics views.")
        st.code(
            "docker compose up -d\n"
            "cp .env.example .env\n"
            "python scripts/generate_synthetic_data.py\n"
            "python scripts/load_data.py\n"
            "streamlit run dashboard/app.py",
            language="bash",
        )
        st.exception(exc)
        st.stop()

    summary = data["summary"]
    if summary.empty:
        st.warning("No dashboard data found. Load the synthetic dataset first.")
        st.stop()

    row = summary.iloc[0]
    funnel = data["funnel"]
    retention = data["retention"]
    subject = data["subject"]
    wait_time = data["wait_time"]
    payment = data["payment"]
    plan_revenue = data["plan_revenue"]
    churn = data["churn"]
    acquisition = data["acquisition"]
    event_trend = data["event_trend"]

    with st.sidebar:
        st.header("Dashboard Context")
        st.metric("Signed-up Users", metric_value(int(row["total_users"])))
        st.metric("Completed Sessions", metric_value(int(row["completed_sessions"])))
        st.metric("Total Revenue", format_inr(row["total_revenue"]))
        st.divider()
        st.write("Data source: local PostgreSQL")
        st.write("Refresh cache every 5 minutes")

    st.subheader("Executive Summary")
    kpi_cols = st.columns(6)
    kpi_cols[0].metric("Activation", metric_value(float(row["activation_rate"]), "%"))
    kpi_cols[1].metric("Completion", metric_value(float(row["session_completion_rate"]), "%"))
    kpi_cols[2].metric("Repeat Usage", metric_value(float(row["repeat_usage_rate"]), "%"))
    kpi_cols[3].metric("Paid Conversion", metric_value(float(row["paid_conversion_rate"]), "%"))
    kpi_cols[4].metric("ARPPU", format_inr(row["arppu"]))
    kpi_cols[5].metric("Avg Rating", metric_value(float(row["avg_rating"])))

    tab_overview, tab_funnel, tab_retention, tab_supply, tab_revenue = st.tabs(
        ["Overview", "Funnel", "Retention", "Supply & Quality", "Revenue"]
    )

    with tab_overview:
        c1, c2 = st.columns([1.25, 1])
        with c1:
            trend_long = event_trend.melt(
                id_vars="event_week",
                value_vars=["app_opens", "questions_submitted", "sessions_completed", "payments_completed"],
                var_name="event_type",
                value_name="events",
            )
            fig = px.line(
                trend_long,
                x="event_week",
                y="events",
                color="event_type",
                markers=True,
                title="Weekly Product Activity",
                color_discrete_sequence=px.colors.qualitative.Set2,
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with c2:
            fig = px.bar(
                acquisition,
                x="users",
                y="acquisition_channel",
                orientation="h",
                color="signup_rate",
                title="Acquisition Mix and Signup Rate",
                color_continuous_scale="Teal",
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)

        i1, i2, i3 = st.columns(3)
        i1.markdown(
            """
            <div class="insight-box">
            <strong>Primary value moment</strong><br>
            The first submitted question is the activation milestone. Users who do not ask a question never reach tutor value.
            </div>
            """,
            unsafe_allow_html=True,
        )
        i2.markdown(
            """
            <div class="insight-box">
            <strong>Operational lever</strong><br>
            Wait time is the clearest supply-side lever because longer waits map directly to lower completion.
            </div>
            """,
            unsafe_allow_html=True,
        )
        i3.markdown(
            """
            <div class="insight-box">
            <strong>Monetization timing</strong><br>
            Payment prompts should follow successful sessions, when users have already experienced learning value.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tab_funnel:
        c1, c2 = st.columns([1.35, 1])
        with c1:
            fig = px.funnel(
                funnel,
                x="user_count",
                y="funnel_stage",
                title="User Journey Funnel",
                color="funnel_stage",
                color_discrete_sequence=px.colors.qualitative.Safe,
            )
            st.plotly_chart(style_chart(fig, height=470), use_container_width=True)
        with c2:
            st.dataframe(
                funnel.rename(
                    columns={
                        "funnel_stage": "Stage",
                        "user_count": "Users",
                        "conversion_from_previous_stage": "From Previous %",
                        "conversion_from_signup": "From Signup %",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
            if len(funnel) > 1:
                dropoffs = funnel.copy()
                dropoffs["previous_users"] = dropoffs["user_count"].shift(1)
                dropoffs["dropped_users"] = dropoffs["previous_users"] - dropoffs["user_count"]
                largest_dropoff = dropoffs.iloc[1:].sort_values("dropped_users", ascending=False).iloc[0]
                st.info(
                    f"Largest absolute drop-off: {int(largest_dropoff['dropped_users']):,} users before "
                    f"{largest_dropoff['funnel_stage'].replace('_', ' ')}."
                )

    with tab_retention:
        week_cols = ["week_0", "week_1", "week_2", "week_3", "week_4"]
        retention_heatmap = retention.set_index("signup_week")[week_cols]
        fig = px.imshow(
            retention_heatmap.T,
            aspect="auto",
            color_continuous_scale="Greens",
            labels=dict(x="Signup Week", y="Retention Week", color="Retention %"),
            title="Weekly Retention Cohorts",
            text_auto=".1f",
        )
        fig.update_yaxes(ticktext=["Week 0", "Week 1", "Week 2", "Week 3", "Week 4"], tickvals=week_cols)
        st.plotly_chart(style_chart(fig, height=440), use_container_width=True)
        st.dataframe(retention, use_container_width=True, hide_index=True)

    with tab_supply:
        c1, c2, c3 = st.columns(3)
        with c1:
            fig = px.bar(
                subject,
                x="subject",
                y="total_questions",
                title="Question Demand by Subject",
                color="subject",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with c2:
            fig = px.bar(
                subject,
                x="subject",
                y="completion_rate",
                title="Completion Rate by Subject",
                color="completion_rate",
                color_continuous_scale="Blues",
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with c3:
            fig = px.bar(
                subject,
                x="subject",
                y="avg_rating",
                title="Average Rating by Subject",
                color="avg_rating",
                color_continuous_scale="Greens",
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            fig = px.line(
                wait_time,
                x="wait_time_bucket",
                y=["completion_rate", "abandonment_rate"],
                markers=True,
                title="Completion vs Abandonment by Wait Time",
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with c2:
            fig = px.bar(
                churn.sort_values("users", ascending=True),
                x="users",
                y="churn_segment",
                orientation="h",
                title="Actionable Churn Segments",
                color="users",
                color_continuous_scale="Reds",
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)

        st.dataframe(subject, use_container_width=True, hide_index=True)

    with tab_revenue:
        c1, c2 = st.columns([1.2, 0.9])
        with c1:
            fig = px.bar(
                payment,
                x="acquisition_channel",
                y="payment_conversion_rate",
                color="total_revenue",
                title="Paid Conversion by Acquisition Channel",
                color_continuous_scale="Viridis",
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)
        with c2:
            fig = px.pie(
                plan_revenue,
                names="plan_type",
                values="revenue",
                title="Revenue by Plan Type",
                hole=0.45,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            st.plotly_chart(style_chart(fig), use_container_width=True)

        st.dataframe(payment, use_container_width=True, hide_index=True)

    st.subheader("Product Recommendations")
    recommendations = [
        "Reduce tutor wait time below 120 seconds for Math and Physics doubts because completion drops as wait time rises.",
        "Improve onboarding for lower-activation acquisition channels before increasing paid acquisition spend.",
        "Trigger re-engagement nudges for users who submitted one question but did not complete a session.",
        "Prioritize tutor supply for high-demand subjects with lower completion rates.",
        "Show paid plan offers after a successful first completed session, when satisfaction and payment intent are higher.",
        "Use referral and school partnership users as quality benchmarks for acquisition and retention.",
    ]

    for index, recommendation in enumerate(recommendations, start=1):
        st.write(f"{index}. {recommendation}")


if __name__ == "__main__":
    main()
