from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data" / "generated"
SQL_DIR = BASE_DIR / "sql"

TABLE_LOAD_ORDER = [
    "users",
    "tutors",
    "questions",
    "sessions",
    "payments",
    "feedback",
    "app_events",
]

TIMESTAMP_COLUMNS = {
    "users": ["signup_date"],
    "app_events": ["event_time"],
    "questions": ["question_created_at"],
    "sessions": ["session_start_time", "session_end_time"],
    "payments": ["payment_date"],
    "feedback": ["feedback_created_at"],
}


def database_url() -> str:
    load_dotenv(BASE_DIR / ".env")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "edtech_analytics")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"


def run_sql_file(engine, file_name: str) -> None:
    sql = (SQL_DIR / file_name).read_text()
    with engine.begin() as conn:
        conn.execute(text(sql))


def load_table(engine, table_name: str) -> None:
    path = DATA_DIR / f"{table_name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. Run scripts/generate_synthetic_data.py first.")
    df = pd.read_csv(path)
    for column in TIMESTAMP_COLUMNS.get(table_name, []):
        df[column] = pd.to_datetime(df[column], errors="coerce")
    df = df.where(pd.notnull(df), None)
    df.to_sql(table_name, engine, if_exists="append", index=False, method="multi", chunksize=1_000)
    print(f"Loaded {len(df):,} rows into {table_name}")


def main() -> None:
    engine = create_engine(database_url())

    print("Creating schema...")
    run_sql_file(engine, "01_schema.sql")

    for table in TABLE_LOAD_ORDER:
        load_table(engine, table)

    print("Creating views and indexes...")
    run_sql_file(engine, "04_views.sql")
    run_sql_file(engine, "05_indexes.sql")

    print("Load complete.")


if __name__ == "__main__":
    main()
