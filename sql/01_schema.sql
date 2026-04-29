CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP TABLE IF EXISTS feedback CASCADE;
DROP TABLE IF EXISTS payments CASCADE;
DROP TABLE IF EXISTS sessions CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
DROP TABLE IF EXISTS app_events CASCADE;
DROP TABLE IF EXISTS tutors CASCADE;
DROP TABLE IF EXISTS users CASCADE;

CREATE TABLE users (
    user_id UUID PRIMARY KEY,
    signup_date TIMESTAMP NOT NULL,
    city VARCHAR(50) NOT NULL,
    grade VARCHAR(20) NOT NULL,
    acquisition_channel VARCHAR(50) NOT NULL,
    device_type VARCHAR(30) NOT NULL,
    user_type VARCHAR(30) NOT NULL,
    is_active BOOLEAN NOT NULL
);

CREATE TABLE app_events (
    event_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    event_name VARCHAR(80) NOT NULL,
    event_time TIMESTAMP NOT NULL,
    device_type VARCHAR(30) NOT NULL,
    session_id UUID NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE questions (
    question_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    subject VARCHAR(40) NOT NULL,
    question_created_at TIMESTAMP NOT NULL,
    question_status VARCHAR(40) NOT NULL,
    difficulty_level VARCHAR(30) NOT NULL,
    source VARCHAR(40) NOT NULL
);

CREATE TABLE tutors (
    tutor_id UUID PRIMARY KEY,
    subject_expertise VARCHAR(40) NOT NULL,
    average_rating NUMERIC(3,2) NOT NULL,
    active_status BOOLEAN NOT NULL,
    city VARCHAR(50) NOT NULL
);

CREATE TABLE sessions (
    session_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    tutor_id UUID REFERENCES tutors(tutor_id) ON DELETE SET NULL,
    question_id UUID REFERENCES questions(question_id) ON DELETE CASCADE,
    session_start_time TIMESTAMP NOT NULL,
    session_end_time TIMESTAMP,
    session_status VARCHAR(40) NOT NULL,
    wait_time_seconds INTEGER NOT NULL,
    session_duration_minutes INTEGER NOT NULL
);

CREATE TABLE payments (
    payment_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    amount NUMERIC(10,2) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    plan_type VARCHAR(30) NOT NULL,
    payment_status VARCHAR(40) NOT NULL,
    payment_method VARCHAR(40) NOT NULL
);

CREATE TABLE feedback (
    feedback_id UUID PRIMARY KEY,
    session_id UUID REFERENCES sessions(session_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    feedback_text TEXT,
    feedback_created_at TIMESTAMP NOT NULL
);

