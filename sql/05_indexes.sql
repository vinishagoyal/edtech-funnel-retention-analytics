CREATE INDEX IF NOT EXISTS idx_users_signup_date ON users(signup_date);
CREATE INDEX IF NOT EXISTS idx_users_acquisition_channel ON users(acquisition_channel);
CREATE INDEX IF NOT EXISTS idx_app_events_user_id ON app_events(user_id);
CREATE INDEX IF NOT EXISTS idx_app_events_event_name ON app_events(event_name);
CREATE INDEX IF NOT EXISTS idx_app_events_event_time ON app_events(event_time);
CREATE INDEX IF NOT EXISTS idx_questions_user_id ON questions(user_id);
CREATE INDEX IF NOT EXISTS idx_questions_subject ON questions(subject);
CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_wait_time_seconds ON sessions(wait_time_seconds);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_payment_date ON payments(payment_date);

