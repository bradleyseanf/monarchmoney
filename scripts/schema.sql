-- Credentials Table
-- USE THIS! (the database.py file is not working)
CREATE TABLE IF NOT EXISTS credentials (
    id SERIAL PRIMARY KEY,
    email VARCHAR NOT NULL UNIQUE,
    encrypted_payload BYTEA NOT NULL,
    monarch_session BYTEA
);

CREATE INDEX IF NOT EXISTS ix_credentials_email ON credentials (email);

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    image_hash VARCHAR NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    parsed_data JSON
);

CREATE INDEX IF NOT EXISTS ix_transactions_image_hash ON transactions (image_hash);
