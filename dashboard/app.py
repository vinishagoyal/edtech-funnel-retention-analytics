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
DATA_DIR = BASE_DIR / "data" / "generated"


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
        div[data-testid="stMetricValue"] {
            font-size: 1.45rem;
        }
        .insight-box {
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 14px 16px;
            background: #f8fafc;
            min-height: 88px;
            margin-bottom: 10px;
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


def style_chart(fig: go.Figure, height: int = 430) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=56, b=36),
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#0f172a", size=13),
        title_font=dict(size=18),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="left", x=0),
        coloraxis_showscale=False,
    )
    fig.update_xaxes(showgrid=False, title=None)
    fig.update_yaxes(gridcolor="#e5e7eb", title=None)
    return fig


def clean_label(value: str) -> str:
    return value.replace("_", " ").title()


def conversion_frame(stages: list[tuple[str, int]]) -> pd.DataFrame:
    rows = []
    signup_users = stages[0][1] if stages else 0
    previous_users = None
    for stage, users in stages:
        rows.append(
            {
                "funnel_stage": stage,
                "user_count": users,
                "conversion_from_previous_stage": round(100.0 * users / previous_users, 2) if previous_users else None,
                "conversion_from_signup": round(100.0 * users / signup_users, 2) if signup_users else None,
            }
        )
        previous_users = users
    return pd.DataFrame(rows)


def week_diff(event_dates: pd.Series, signup_weeks: pd.Series) -> pd.Series:
    return ((event_dates.dt.normalize() - signup_weeks).dt.days // 7).astype("int64")


def wait_bucket(seconds: pd.Series) -> pd.Series:
    return pd.cut(
        seconds,
        bins=[-1, 60, 120, 180, 300, float("inf")],
        labels=["0 to 60 sec", "61 to 120 sec", "121 to 180 sec", "181 to 300 sec", "300+ sec"],
    )


@st.cache_data(ttl=300)
def load_csv_dashboard_data() -> dict[str, pd.DataFrame]:
    required = ["users", "app_events", "questions", "sessions", "payments", "feedback"]
    missing = [name for name in required if not (DATA_DIR / f"{name}.csv").exists()]
    if missing:
        raise FileNotFoundError(
            "Missing generated CSV files: "
            + ", ".join(f"{name}.csv" for name in missing)
            + ". Run python3 scripts/generate_synthetic_data.py first."
        )

    users = pd.read_csv(DATA_DIR / "users.csv", parse_dates=["signup_date"])
    events = pd.read_csv(DATA_DIR / "app_events.csv", parse_dates=["event_time"])
    questions = pd.read_csv(DATA_DIR / "questions.csv", parse_dates=["question_created_at"])
    sessions = pd.read_csv(DATA_DIR / "sessions.csv", parse_dates=["session_start_time", "session_end_time"])
    payments = pd.read_csv(DATA_DIR / "payments.csv", parse_dates=["payment_date"])
    feedback = pd.read_csv(DATA_DIR / "feedback.csv", parse_dates=["feedback_created_at"])

    signed_up = users[users["user_type"] == "signed_up"]
    completed_sessions = sessions[sessions["session_status"] == "completed"]
    completed_payments = payments[payments["payment_status"] == "completed"]
    activated_users = questions["user_id"].nunique()
    repeat_users = sessions.groupby("user_id").size().loc[lambda count: count >= 2].index.nunique()
    paid_users = completed_payments["user_id"].nunique()
    total_revenue = completed_payments["amount"].sum()

    summary = pd.DataFrame(
        [
            {
                "total_users": signed_up["user_id"].nunique(),
                "activated_users": activated_users,
                "total_sessions": sessions["session_id"].nunique(),
                "completed_sessions": completed_sessions["session_id"].nunique(),
                "activation_rate": round(100.0 * activated_users / max(signed_up["user_id"].nunique(), 1), 2),
                "session_completion_rate": round(100.0 * len(completed_sessions) / max(len(sessions), 1), 2),
                "repeat_usage_rate": round(100.0 * repeat_users / max(activated_users, 1), 2),
                "paid_conversion_rate": round(100.0 * paid_users / max(signed_up["user_id"].nunique(), 1), 2),
                "total_revenue": round(total_revenue, 2),
                "arppu": round(total_revenue / paid_users, 2) if paid_users else 0,
                "avg_wait_seconds": round(sessions["wait_time_seconds"].mean(), 0),
                "avg_rating": round(feedback["rating"].mean(), 2),
            }
        ]
    )

    funnel = conversion_frame(
        [
            ("signed_up", signed_up["user_id"].nunique()),
            ("onboarding_completed", events.loc[events["event_name"] == "onboarding_completed", "user_id"].nunique()),
            ("question_submitted", events.loc[events["event_name"] == "question_submitted", "user_id"].nunique()),
            ("tutor_connected", events.loc[events["event_name"] == "tutor_connected", "user_id"].nunique()),
            ("session_completed", completed_sessions["user_id"].nunique()),
            ("repeat_session", repeat_users),
            ("payment_completed", paid_users),
        ]
    )

    cohorts = signed_up[["user_id", "signup_date"]].copy()
    cohorts["signup_week"] = cohorts["signup_date"].dt.to_period("W").dt.start_time
    active_events = events[events["event_name"].isin(["app_opened", "question_submitted", "session_completed"])].merge(
        cohorts[["user_id", "signup_week"]], on="user_id", how="inner"
    )
    active_events["active_week"] = week_diff(active_events["event_time"], active_events["signup_week"])
    active_events = active_events[active_events["active_week"].between(0, 4)]
    cohort_sizes = cohorts.groupby("signup_week")["user_id"].nunique().rename("cohort_users")
    retention_rows = []
    for signup_week, cohort_users in cohort_sizes.items():
        row = {"signup_week": signup_week.date(), "cohort_users": cohort_users}
        cohort_activity = active_events[active_events["signup_week"] == signup_week]
        for week in range(5):
            active_users = cohort_activity.loc[cohort_activity["active_week"] == week, "user_id"].nunique()
            row[f"week_{week}"] = round(100.0 * active_users / cohort_users, 2) if cohort_users else 0
        retention_rows.append(row)
    retention = pd.DataFrame(retention_rows)

    subject_joined = questions.merge(sessions, on="question_id", how="left").merge(feedback[["session_id", "rating"]], on="session_id", how="left")
    subject = (
        subject_joined.groupby("subject")
        .agg(
            total_questions=("question_id", "nunique"),
            completed_sessions=("session_id", lambda value: subject_joined.loc[value.index, "session_status"].eq("completed").sum()),
            avg_rating=("rating", "mean"),
        )
        .reset_index()
    )
    subject["completion_rate"] = (100.0 * subject["completed_sessions"] / subject["total_questions"]).round(2)
    subject["avg_rating"] = subject["avg_rating"].round(2)
    subject = subject.sort_values("total_questions", ascending=False)

    wait_sessions = sessions.copy()
    wait_sessions["wait_time_bucket"] = wait_bucket(wait_sessions["wait_time_seconds"])
    wait_joined = wait_sessions.merge(feedback[["session_id", "rating"]], on="session_id", how="left")
    wait_time = (
        wait_joined.groupby("wait_time_bucket", observed=False)
        .agg(
            total_sessions=("session_id", "count"),
            completed_sessions=("session_status", lambda value: value.eq("completed").sum()),
            abandoned_sessions=("session_status", lambda value: value.ne("completed").sum()),
            avg_feedback_rating=("rating", "mean"),
        )
        .reset_index()
    )
    wait_time["completion_rate"] = (100.0 * wait_time["completed_sessions"] / wait_time["total_sessions"]).round(2)
    wait_time["abandonment_rate"] = (100.0 * wait_time["abandoned_sessions"] / wait_time["total_sessions"]).round(2)
    wait_time["avg_feedback_rating"] = wait_time["avg_feedback_rating"].round(2)

    payment = users.merge(payments, on="user_id", how="left")
    payment = (
        payment.groupby("acquisition_channel")
        .agg(
            total_users=("user_id", "nunique"),
            paid_users=("payment_status", lambda value: payment.loc[value.index].query("payment_status == 'completed'")["user_id"].nunique()),
            total_revenue=("amount", lambda value: payment.loc[value.index].query("payment_status == 'completed'")["amount"].sum()),
        )
        .reset_index()
    )
    payment["payment_conversion_rate"] = (100.0 * payment["paid_users"] / payment["total_users"]).round(2)
    payment["arppu"] = (payment["total_revenue"] / payment["paid_users"].replace(0, pd.NA)).round(2).fillna(0)
    payment["total_revenue"] = payment["total_revenue"].round(2)
    payment = payment.sort_values("payment_conversion_rate", ascending=False)

    plan_revenue = (
        completed_payments.groupby("plan_type")["amount"]
        .sum()
        .round(2)
        .rename("revenue")
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    session_counts = sessions.groupby("user_id").agg(total_sessions=("session_id", "count"), completed_sessions=("session_status", lambda x: x.eq("completed").sum()))
    signed_never_asked = signed_up[~signed_up["user_id"].isin(questions["user_id"])]["user_id"].nunique()
    question_counts = questions.groupby("user_id").size()
    asked_one = question_counts[question_counts == 1].index
    no_completed = session_counts.reindex(asked_one).fillna(0)["completed_sessions"].eq(0).sum()
    completed_one = session_counts["completed_sessions"].eq(1).sum()
    payment_viewers = set(events.loc[events["event_name"] == "payment_page_viewed", "user_id"])
    payers = set(completed_payments["user_id"])
    churn = pd.DataFrame(
        [
            {"churn_segment": "Signed up, never asked question", "users": signed_never_asked},
            {"churn_segment": "Asked one question, no completed session", "users": int(no_completed)},
            {"churn_segment": "Completed one session, never returned", "users": int(completed_one)},
            {"churn_segment": "Viewed payment page, did not pay", "users": len(payment_viewers - payers)},
        ]
    )

    acquisition = (
        users.groupby("acquisition_channel")
        .agg(users=("user_id", "count"), signed_up_users=("user_type", lambda value: value.eq("signed_up").sum()))
        .reset_index()
    )
    acquisition["signup_rate"] = (100.0 * acquisition["signed_up_users"] / acquisition["users"]).round(2)
    acquisition = acquisition.sort_values("users", ascending=False)

    event_trend = events.copy()
    event_trend["event_week"] = event_trend["event_time"].dt.to_period("W").dt.start_time.dt.date
    event_trend = (
        event_trend.pivot_table(index="event_week", columns="event_name", values="event_id", aggfunc="count", fill_value=0)
        .reset_index()
        .rename_axis(None, axis=1)
    )
    for column in ["app_opened", "question_submitted", "session_completed", "payment_completed"]:
        if column not in event_trend:
            event_trend[column] = 0
    event_trend = event_trend[["event_week", "app_opened", "question_submitted", "session_completed", "payment_completed"]]
    event_trend = event_trend.rename(columns={"app_opened": "app_opens", "question_submitted": "questions_submitted", "session_completed": "sessions_completed", "payment_completed": "payments_completed"})

    return {
        "summary": summary,
        "funnel": funnel,
        "retention": retention,
        "subject": subject,
        "wait_time": wait_time,
        "payment": payment,
        "plan_revenue": plan_revenue,
        "churn": churn,
        "acquisition": acquisition,
        "event_trend": event_trend,
        "source": pd.DataFrame([{"name": "Generated CSV fallback"}]),
    }


def load_dashboard_data() -> dict[str, pd.DataFrame]:
    data = {
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
    data["source"] = pd.DataFrame([{"name": "PostgreSQL"}])
    return data


def main() -> None:
    st.title("EdTech Product Analytics Dashboard")
    st.caption("Synthetic product analytics dashboard for funnel, retention, tutor supply, session quality, and monetization analysis.")

    try:
        data = load_dashboard_data()
    except SQLAlchemyError:
        try:
            data = load_csv_dashboard_data()
        except FileNotFoundError as exc:
            st.error("Could not connect to PostgreSQL, and generated CSV files are missing.")
            st.code(
                "python3 scripts/generate_synthetic_data.py\n"
                "python3 -m streamlit run dashboard/app.py",
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
        st.write(f"Data source: {data['source'].iloc[0]['name']}")
        st.write("Refresh cache every 5 minutes")

    st.subheader("Executive Summary")
    kpi_cols = st.columns(3)
    kpi_cols[0].metric("Activation", metric_value(float(row["activation_rate"]), "%"))
    kpi_cols[1].metric("Completion", metric_value(float(row["session_completion_rate"]), "%"))
    kpi_cols[2].metric("Repeat Usage", metric_value(float(row["repeat_usage_rate"]), "%"))
    kpi_cols = st.columns(3)
    kpi_cols[0].metric("Paid Conversion", metric_value(float(row["paid_conversion_rate"]), "%"))
    kpi_cols[1].metric("ARPPU", format_inr(row["arppu"]))
    kpi_cols[2].metric("Avg Rating", metric_value(float(row["avg_rating"])))

    tab_overview, tab_funnel, tab_retention, tab_supply, tab_revenue = st.tabs(
        ["Overview", "Funnel", "Retention", "Supply & Quality", "Revenue"]
    )

    with tab_overview:
        trend_long = event_trend.melt(
            id_vars="event_week",
            value_vars=["app_opens", "questions_submitted", "sessions_completed", "payments_completed"],
            var_name="event_type",
            value_name="events",
        )
        trend_long["event_type"] = trend_long["event_type"].map(
            {
                "app_opens": "App Opens",
                "questions_submitted": "Questions",
                "sessions_completed": "Sessions",
                "payments_completed": "Payments",
            }
        )
        fig = px.line(
            trend_long,
            x="event_week",
            y="events",
            color="event_type",
            markers=True,
            title="Weekly Activity",
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        st.plotly_chart(style_chart(fig, height=460), use_container_width=True)

        acquisition_chart = acquisition.sort_values("users", ascending=True)
        fig = px.bar(
            acquisition_chart,
            x="users",
            y="acquisition_channel",
            orientation="h",
            text="users",
            title="Acquisition Mix",
            color_discrete_sequence=["#2f80ed"],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(l=150, r=40, t=56, b=32))
        st.plotly_chart(style_chart(fig, height=390), use_container_width=True)

        st.markdown(
            """
            <div class="insight-box">
            <strong>Primary value moment</strong><br>
            The first submitted question is the activation milestone. Users who do not ask a question never reach tutor value.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="insight-box">
            <strong>Operational lever</strong><br>
            Wait time is the clearest supply-side lever because longer waits map directly to lower completion.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="insight-box">
            <strong>Monetization timing</strong><br>
            Payment prompts should follow successful sessions, when users have already experienced learning value.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with tab_funnel:
        funnel_chart = funnel.copy()
        funnel_chart["stage_label"] = funnel_chart["funnel_stage"].map(clean_label)
        fig = px.funnel(
            funnel_chart,
            x="user_count",
            y="stage_label",
            title="User Journey Funnel",
            color_discrete_sequence=["#2f80ed"],
        )
        fig.update_layout(margin=dict(l=150, r=30, t=56, b=30), showlegend=False)
        st.plotly_chart(style_chart(fig, height=520), use_container_width=True)

        funnel_table = funnel.rename(
            columns={
                "funnel_stage": "Stage",
                "user_count": "Users",
                "conversion_from_previous_stage": "From Previous %",
                "conversion_from_signup": "From Signup %",
            }
        )
        funnel_table["Stage"] = funnel_table["Stage"].map(clean_label)
        st.dataframe(funnel_table, use_container_width=True, hide_index=True)
        if len(funnel) > 1:
            dropoffs = funnel.copy()
            dropoffs["previous_users"] = dropoffs["user_count"].shift(1)
            dropoffs["dropped_users"] = dropoffs["previous_users"] - dropoffs["user_count"]
            largest_dropoff = dropoffs.iloc[1:].sort_values("dropped_users", ascending=False).iloc[0]
            st.info(
                f"Largest absolute drop-off: {int(largest_dropoff['dropped_users']):,} users before "
                f"{clean_label(largest_dropoff['funnel_stage'])}."
            )

    with tab_retention:
        week_cols = ["week_0", "week_1", "week_2", "week_3", "week_4"]
        retention_heatmap = retention.set_index("signup_week")[week_cols]
        fig = px.imshow(
            retention_heatmap.T,
            aspect="auto",
            color_continuous_scale="Greens",
            labels=dict(x="Signup Week", y="Retention Week", color="Retention %"),
            title="Retention Cohorts",
            text_auto=".1f",
        )
        fig.update_yaxes(ticktext=["Week 0", "Week 1", "Week 2", "Week 3", "Week 4"], tickvals=week_cols)
        fig.update_xaxes(tickangle=35)
        st.plotly_chart(style_chart(fig, height=500), use_container_width=True)
        st.dataframe(retention, use_container_width=True, hide_index=True)

    with tab_supply:
        subject_chart = subject.sort_values("total_questions", ascending=True)
        fig = px.bar(
            subject_chart,
            x="total_questions",
            y="subject",
            orientation="h",
            text="total_questions",
            title="Question Demand by Subject",
            color_discrete_sequence=["#2f80ed"],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(l=100, r=40, t=56, b=32), showlegend=False)
        st.plotly_chart(style_chart(fig, height=370), use_container_width=True)

        quality_chart = subject.sort_values("completion_rate", ascending=True)
        fig = px.bar(
            quality_chart,
            x="completion_rate",
            y="subject",
            orientation="h",
            text="completion_rate",
            title="Completion Rate by Subject",
            color_discrete_sequence=["#27ae60"],
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
        fig.update_xaxes(range=[0, 100])
        fig.update_layout(margin=dict(l=100, r=40, t=56, b=32), showlegend=False)
        st.plotly_chart(style_chart(fig, height=370), use_container_width=True)

        wait_chart = wait_time.melt(
            id_vars="wait_time_bucket",
            value_vars=["completion_rate", "abandonment_rate"],
            var_name="metric",
            value_name="rate",
        )
        wait_chart["metric"] = wait_chart["metric"].map(
            {"completion_rate": "Completed", "abandonment_rate": "Abandoned"}
        )
        fig = px.line(
            wait_chart,
            x="wait_time_bucket",
            y="rate",
            color="metric",
            markers=True,
            title="Wait Time Impact",
            color_discrete_sequence=["#27ae60", "#eb5757"],
        )
        fig.update_yaxes(range=[0, 100], ticksuffix="%")
        st.plotly_chart(style_chart(fig, height=420), use_container_width=True)

        churn_chart = churn.sort_values("users", ascending=True)
        fig = px.bar(
            churn_chart,
            x="users",
            y="churn_segment",
            orientation="h",
            text="users",
            title="Churn Segments",
            color_discrete_sequence=["#eb5757"],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(l=240, r=40, t=56, b=32), showlegend=False)
        st.plotly_chart(style_chart(fig, height=380), use_container_width=True)

        st.dataframe(subject, use_container_width=True, hide_index=True)

    with tab_revenue:
        payment_chart = payment.sort_values("payment_conversion_rate", ascending=True)
        fig = px.bar(
            payment_chart,
            x="payment_conversion_rate",
            y="acquisition_channel",
            orientation="h",
            text="payment_conversion_rate",
            title="Paid Conversion by Channel",
            color_discrete_sequence=["#2f80ed"],
        )
        fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside", cliponaxis=False)
        fig.update_xaxes(range=[0, max(45, float(payment_chart["payment_conversion_rate"].max()) + 8)], ticksuffix="%")
        fig.update_layout(margin=dict(l=160, r=40, t=56, b=32), showlegend=False)
        st.plotly_chart(style_chart(fig, height=420), use_container_width=True)

        plan_chart = plan_revenue.sort_values("revenue", ascending=True)
        fig = px.bar(
            plan_chart,
            x="revenue",
            y="plan_type",
            orientation="h",
            text="revenue",
            title="Revenue by Plan",
            color_discrete_sequence=["#27ae60"],
        )
        fig.update_traces(texttemplate="INR %{text:,.0f}", textposition="outside", cliponaxis=False)
        fig.update_layout(margin=dict(l=110, r=70, t=56, b=32), showlegend=False)
        st.plotly_chart(style_chart(fig, height=320), use_container_width=True)

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
