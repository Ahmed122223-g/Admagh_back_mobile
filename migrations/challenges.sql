-- Add columns to users table
ALTER TABLE users ADD COLUMN gold_cups INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN silver_cups INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN bronze_cups INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN challenges_count INTEGER DEFAULT 0;

-- Create challenges table
CREATE TABLE challenges (
    id SERIAL PRIMARY KEY,
    creator_id BIGINT NOT NULL,
    name VARCHAR NOT NULL,
    description TEXT,
    duration_minutes INTEGER NOT NULL,
    is_quiz BOOLEAN DEFAULT FALSE,
    lifespan_hours INTEGER DEFAULT 24,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT (NOW() AT TIME ZONE 'utc'),
    expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    FOREIGN KEY (creator_id) REFERENCES users(id)
);

CREATE INDEX ix_challenges_id ON challenges (id);

-- Create challenge_participants table
CREATE TABLE challenge_participants (
    id SERIAL PRIMARY KEY,
    challenge_id INTEGER NOT NULL,
    user_id BIGINT NOT NULL,
    status VARCHAR DEFAULT 'invited',
    start_time TIMESTAMP WITHOUT TIME ZONE,
    end_time TIMESTAMP WITHOUT TIME ZONE,
    time_taken_seconds INTEGER,
    score FLOAT,
    FOREIGN KEY (challenge_id) REFERENCES challenges(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE INDEX ix_challenge_participants_id ON challenge_participants (id);

-- Create quizzes table
CREATE TABLE quizzes (
    id SERIAL PRIMARY KEY,
    challenge_id INTEGER NOT NULL UNIQUE,
    duration_minutes INTEGER NOT NULL,
    FOREIGN KEY (challenge_id) REFERENCES challenges(id)
);

CREATE INDEX ix_quizzes_id ON quizzes (id);

-- Create questions table
CREATE TABLE questions (
    id SERIAL PRIMARY KEY,
    quiz_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    type VARCHAR NOT NULL,
    explanation TEXT,
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id)
);

CREATE INDEX ix_questions_id ON questions (id);

-- Create question_options table
CREATE TABLE question_options (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL,
    text VARCHAR NOT NULL,
    is_correct BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

CREATE INDEX ix_question_options_id ON question_options (id);
