-- backend/scripts/create_ai_learning_feedback_table.sql
CREATE TABLE IF NOT EXISTS ai_learning_feedback (
    id SERIAL PRIMARY KEY,
    pattern_number VARCHAR(255) NOT NULL,
    ai_recommendation TEXT NOT NULL,
    actual_action TEXT NOT NULL,
    result BOOLEAN NOT NULL,
    helpful_points TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
