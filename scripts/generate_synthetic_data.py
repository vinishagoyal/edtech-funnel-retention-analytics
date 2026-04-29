from __future__ import annotations

import json
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


SEED = 42
fake = Faker("en_IN")
Faker.seed(SEED)
random.seed(SEED)
np.random.seed(SEED)

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = BASE_DIR / "data" / "generated"

N_USERS = 5_000
N_EVENTS = 40_000
N_QUESTIONS = 12_000
N_TUTORS = 500
N_SESSIONS = 8_000
N_PAYMENTS = 1_500
N_FEEDBACK = 5_000

CITIES = ["Delhi", "Gurgaon", "Mumbai", "Bangalore", "Pune", "Hyderabad", "Jaipur", "Lucknow"]
GRADES = ["Grade 8", "Grade 9", "Grade 10", "Grade 11", "Grade 12", "Dropper"]
CHANNELS = ["Organic", "Google Ads", "Instagram", "Referral", "YouTube", "School Partnership"]
DEVICES = ["Android", "iOS", "Web"]
SUBJECTS = ["Math", "Physics", "Chemistry", "Biology", "English"]
DIFFICULTIES = ["easy", "medium", "hard"]
SOURCES = ["homework", "exam_prep", "assignment", "concept_doubt"]
PLAN_PRICES = {"weekly": 199.0, "monthly": 499.0, "quarterly": 1299.0}
PAYMENT_METHODS = ["UPI", "Card", "Net Banking", "Wallet"]

CHANNEL_SIGNUP_RATE = {
    "Organic": 0.82,
    "Google Ads": 0.76,
    "Instagram": 0.68,
    "Referral": 0.88,
    "YouTube": 0.73,
    "School Partnership": 0.90,
}

CHANNEL_PAYMENT_MULTIPLIER = {
    "Organic": 1.05,
    "Google Ads": 0.95,
    "Instagram": 0.72,
    "Referral": 1.35,
    "YouTube": 0.90,
    "School Partnership": 1.25,
}


def new_id() -> str:
    return str(uuid.uuid4())


def bounded_rating(value: float) -> float:
    return round(max(1.0, min(5.0, value)), 2)


def random_date(start: datetime, end: datetime) -> datetime:
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, seconds))


def event(user_id: str, event_name: str, event_time: datetime, device_type: str, session_id: str | None = None, **metadata) -> dict:
    return {
        "event_id": new_id(),
        "user_id": user_id,
        "event_name": event_name,
        "event_time": event_time,
        "device_type": device_type,
        "session_id": session_id,
        "metadata": json.dumps(metadata),
    }


def generate_users() -> pd.DataFrame:
    start = datetime(2025, 1, 1)
    end = datetime(2025, 6, 30)
    rows = []

    for _ in range(N_USERS):
        channel = random.choices(CHANNELS, weights=[24, 18, 20, 14, 14, 10], k=1)[0]
        signup_rate = CHANNEL_SIGNUP_RATE[channel]
        signed_up = random.random() < signup_rate
        rows.append(
            {
                "user_id": new_id(),
                "signup_date": random_date(start, end),
                "city": random.choice(CITIES),
                "grade": random.choices(GRADES, weights=[15, 17, 22, 19, 18, 9], k=1)[0],
                "acquisition_channel": channel,
                "device_type": random.choices(DEVICES, weights=[72, 22, 6], k=1)[0],
                "user_type": "signed_up" if signed_up else "installed_only",
                "is_active": signed_up and random.random() < 0.62,
            }
        )
    return pd.DataFrame(rows)


def generate_tutors() -> pd.DataFrame:
    rows = []
    for _ in range(N_TUTORS):
        subject = random.choices(SUBJECTS, weights=[34, 28, 17, 12, 9], k=1)[0]
        rows.append(
            {
                "tutor_id": new_id(),
                "subject_expertise": subject,
                "average_rating": bounded_rating(np.random.normal(4.25, 0.45)),
                "active_status": random.random() < 0.86,
                "city": random.choice(CITIES),
            }
        )
    return pd.DataFrame(rows)


def generate_questions(users: pd.DataFrame) -> pd.DataFrame:
    signed_up = users[users["user_type"] == "signed_up"].copy()
    weights = np.where(signed_up["is_active"], 2.3, 0.8)
    weights = weights / weights.sum()
    chosen_users = np.random.choice(signed_up["user_id"], size=N_QUESTIONS, replace=True, p=weights)
    user_lookup = users.set_index("user_id")

    rows = []
    for user_id in chosen_users:
        signup_date = user_lookup.loc[user_id, "signup_date"]
        subject = random.choices(SUBJECTS, weights=[38, 29, 15, 10, 8], k=1)[0]
        rows.append(
            {
                "question_id": new_id(),
                "user_id": user_id,
                "subject": subject,
                "question_created_at": signup_date + timedelta(hours=random.randint(1, 24 * 42), minutes=random.randint(0, 59)),
                "question_status": "submitted",
                "difficulty_level": random.choices(DIFFICULTIES, weights=[24, 50, 26], k=1)[0],
                "source": random.choices(SOURCES, weights=[34, 28, 18, 20], k=1)[0],
            }
        )
    return pd.DataFrame(rows)


def generate_sessions(questions: pd.DataFrame, tutors: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    session_questions = questions.sample(N_SESSIONS, random_state=SEED).copy().reset_index(drop=True)
    tutor_by_subject = {subject: tutors[tutors["subject_expertise"] == subject] for subject in SUBJECTS}
    rows = []
    status_by_question = {}

    for _, q in session_questions.iterrows():
        subject_tutors = tutor_by_subject[q["subject"]]
        tutor = subject_tutors.sample(1, random_state=random.randint(1, 1_000_000)).iloc[0]
        wait = int(max(12, np.random.gamma(shape=2.0, scale=70)))

        if wait <= 60:
            complete_prob = 0.86
        elif wait <= 120:
            complete_prob = 0.75
        elif wait <= 180:
            complete_prob = 0.63
        elif wait <= 300:
            complete_prob = 0.48
        else:
            complete_prob = 0.32

        if q["subject"] in ["Math", "Physics"]:
            complete_prob -= 0.04
        if tutor["active_status"]:
            complete_prob += 0.04

        completed = random.random() < complete_prob
        if completed:
            status = "completed"
            duration = int(max(8, np.random.normal(24, 8)))
        else:
            status = random.choices(
                ["abandoned_before_start", "dropped_mid_session", "tutor_unavailable"],
                weights=[50, 30, 20],
                k=1,
            )[0]
            duration = 0 if status != "dropped_mid_session" else random.randint(3, 11)

        start_time = q["question_created_at"] + timedelta(seconds=wait)
        end_time = start_time + timedelta(minutes=duration) if duration > 0 else None
        session_id = new_id()
        rows.append(
            {
                "session_id": session_id,
                "user_id": q["user_id"],
                "tutor_id": tutor["tutor_id"],
                "question_id": q["question_id"],
                "session_start_time": start_time,
                "session_end_time": end_time,
                "session_status": status,
                "wait_time_seconds": wait,
                "session_duration_minutes": duration,
            }
        )
        status_by_question[q["question_id"]] = "resolved" if completed else status

    sessions = pd.DataFrame(rows)
    completed_count = (sessions["session_status"] == "completed").sum()
    if completed_count < N_FEEDBACK:
        needed = N_FEEDBACK - completed_count
        candidates = sessions[sessions["session_status"] != "completed"].head(needed).index
        sessions.loc[candidates, "session_status"] = "completed"
        sessions.loc[candidates, "session_duration_minutes"] = np.random.randint(12, 36, size=len(candidates))
        sessions.loc[candidates, "session_end_time"] = sessions.loc[candidates, "session_start_time"] + pd.to_timedelta(
            sessions.loc[candidates, "session_duration_minutes"], unit="m"
        )

    status_map = sessions.set_index("question_id")["session_status"].to_dict()
    questions = questions.copy()
    questions["question_status"] = questions.apply(
        lambda row: "resolved"
        if status_map.get(row["question_id"]) == "completed"
        else ("tutor_connected" if row["question_id"] in status_map else row["question_status"]),
        axis=1,
    )
    questions.loc[~questions["question_id"].isin(status_map.keys()) & (np.random.random(len(questions)) < 0.18), "question_status"] = "abandoned"
    return sessions, questions


def generate_feedback(sessions: pd.DataFrame) -> pd.DataFrame:
    completed = sessions[sessions["session_status"] == "completed"].sample(N_FEEDBACK, random_state=SEED)
    rows = []
    for _, s in completed.iterrows():
        wait_penalty = 0.0 if s["wait_time_seconds"] <= 120 else -0.45 if s["wait_time_seconds"] <= 300 else -0.85
        base = 4.45 + wait_penalty + np.random.normal(0, 0.55)
        rating = int(round(max(1, min(5, base))))
        rows.append(
            {
                "feedback_id": new_id(),
                "session_id": s["session_id"],
                "user_id": s["user_id"],
                "rating": rating,
                "feedback_text": random.choice(
                    [
                        "Tutor explained the concept clearly.",
                        "Fast connection and useful solution.",
                        "Good session, but I wanted more examples.",
                        "The wait time felt high.",
                        "Helpful for homework doubt solving.",
                        "Great explanation for exam preparation.",
                    ]
                ),
                "feedback_created_at": s["session_end_time"] + timedelta(minutes=random.randint(1, 45)),
            }
        )
    return pd.DataFrame(rows)


def generate_payments(users: pd.DataFrame, sessions: pd.DataFrame, feedback: pd.DataFrame) -> pd.DataFrame:
    completed_users = set(sessions.loc[sessions["session_status"] == "completed", "user_id"])
    user_avg_rating = feedback.groupby("user_id")["rating"].mean().to_dict()
    candidates = users[users["user_id"].isin(completed_users)].copy()
    probabilities = []

    for _, u in candidates.iterrows():
        rating = user_avg_rating.get(u["user_id"], 3.5)
        base = 0.18 + max(0, rating - 3.5) * 0.08
        if u["acquisition_channel"] in CHANNEL_PAYMENT_MULTIPLIER:
            base *= CHANNEL_PAYMENT_MULTIPLIER[u["acquisition_channel"]]
        if u["grade"] in ["Grade 11", "Grade 12", "Dropper"]:
            base *= 1.18
        probabilities.append(max(0.02, min(0.55, base)))

    probabilities = np.array(probabilities)
    probabilities = probabilities / probabilities.sum()
    selected = np.random.choice(candidates["user_id"], size=N_PAYMENTS, replace=False, p=probabilities)
    user_lookup = users.set_index("user_id")
    first_session = sessions.groupby("user_id")["session_start_time"].min().to_dict()

    rows = []
    for user_id in selected:
        plan = random.choices(["weekly", "monthly", "quarterly"], weights=[42, 45, 13], k=1)[0]
        status = "completed" if random.random() < 0.92 else random.choice(["failed", "refunded"])
        paid_at = first_session[user_id] + timedelta(days=random.randint(0, 21), hours=random.randint(0, 23))
        rows.append(
            {
                "payment_id": new_id(),
                "user_id": user_id,
                "amount": PLAN_PRICES[plan],
                "payment_date": paid_at,
                "plan_type": plan,
                "payment_status": status,
                "payment_method": random.choice(PAYMENT_METHODS),
            }
        )
    return pd.DataFrame(rows)


def generate_events(users: pd.DataFrame, questions: pd.DataFrame, sessions: pd.DataFrame, payments: pd.DataFrame) -> pd.DataFrame:
    events: list[dict] = []
    user_lookup = users.set_index("user_id")
    signed_up_users = users[users["user_type"] == "signed_up"]

    for _, u in users.iterrows():
        events.append(event(u["user_id"], "app_install", u["signup_date"] - timedelta(minutes=random.randint(5, 180)), u["device_type"]))
        if u["user_type"] == "signed_up":
            events.append(event(u["user_id"], "signup_completed", u["signup_date"], u["device_type"]))
            if random.random() < 0.88:
                events.append(event(u["user_id"], "onboarding_started", u["signup_date"] + timedelta(minutes=random.randint(1, 15)), u["device_type"]))
            if random.random() < 0.78:
                events.append(event(u["user_id"], "onboarding_completed", u["signup_date"] + timedelta(minutes=random.randint(8, 45)), u["device_type"]))

    submitted_questions = questions.sample(min(9_200, len(questions)), random_state=SEED)
    for _, q in submitted_questions.iterrows():
        device = user_lookup.loc[q["user_id"], "device_type"]
        if random.random() < 0.35:
            events.append(event(q["user_id"], "question_started", q["question_created_at"] - timedelta(minutes=random.randint(1, 8)), device, subject=q["subject"]))
        events.append(event(q["user_id"], "question_submitted", q["question_created_at"], device, subject=q["subject"], source=q["source"]))

    for _, s in sessions.iterrows():
        device = user_lookup.loc[s["user_id"], "device_type"]
        if random.random() < 0.62:
            events.append(event(s["user_id"], "tutor_search_started", s["session_start_time"] - timedelta(seconds=s["wait_time_seconds"]), device, s["session_id"]))
        if s["session_status"] in ["completed", "dropped_mid_session"] and random.random() < 0.88:
            events.append(event(s["user_id"], "tutor_connected", s["session_start_time"], device, s["session_id"]))
            events.append(event(s["user_id"], "session_started", s["session_start_time"], device, s["session_id"]))
        if s["session_status"] == "completed" and random.random() < 0.86:
            events.append(event(s["user_id"], "session_completed", s["session_end_time"], device, s["session_id"]))

    payment_view_users = set(payments["user_id"])
    extra_intent_users = signed_up_users.sample(900, random_state=SEED + 1)["user_id"]
    for user_id in list(payment_view_users) + list(extra_intent_users):
        u = user_lookup.loc[user_id]
        events.append(event(user_id, "payment_page_viewed", u["signup_date"] + timedelta(days=random.randint(1, 40)), u["device_type"]))

    for _, p in payments[payments["payment_status"] == "completed"].iterrows():
        device = user_lookup.loc[p["user_id"], "device_type"]
        events.append(event(p["user_id"], "payment_completed", p["payment_date"], device, plan_type=p["plan_type"], amount=float(p["amount"])))

    if len(events) > N_EVENTS:
        priority = {"app_opened": 1, "question_started": 2, "tutor_search_started": 3, "onboarding_started": 4}
        events = sorted(events, key=lambda x: priority.get(x["event_name"], 10), reverse=True)[:N_EVENTS]

    while len(events) < N_EVENTS:
        u = signed_up_users.sample(1, random_state=random.randint(1, 1_000_000)).iloc[0]
        completed_sessions = sessions[(sessions["user_id"] == u["user_id"]) & (sessions["session_status"] == "completed")]
        retained = len(completed_sessions) > 0 and random.random() < 0.72
        max_days = 35 if retained else 10
        events.append(event(u["user_id"], "app_opened", u["signup_date"] + timedelta(days=random.randint(0, max_days)), u["device_type"]))

    events_df = pd.DataFrame(events).sample(frac=1, random_state=SEED).reset_index(drop=True)
    return events_df.head(N_EVENTS)


def write_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    users = generate_users()
    tutors = generate_tutors()
    questions = generate_questions(users)
    sessions, questions = generate_sessions(questions, tutors)
    feedback = generate_feedback(sessions)
    payments = generate_payments(users, sessions, feedback)
    events = generate_events(users, questions, sessions, payments)

    write_csv(users, "users")
    write_csv(tutors, "tutors")
    write_csv(questions, "questions")
    write_csv(sessions, "sessions")
    write_csv(feedback, "feedback")
    write_csv(payments, "payments")
    write_csv(events, "app_events")

    print("Synthetic data generated in data/generated/")
    print(
        {
            "users": len(users),
            "app_events": len(events),
            "questions": len(questions),
            "tutors": len(tutors),
            "sessions": len(sessions),
            "payments": len(payments),
            "feedback": len(feedback),
        }
    )


if __name__ == "__main__":
    main()

