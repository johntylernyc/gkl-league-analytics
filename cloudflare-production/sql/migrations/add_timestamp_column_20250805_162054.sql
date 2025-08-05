-- Add timestamp column to transactions table
ALTER TABLE transactions ADD COLUMN timestamp INTEGER DEFAULT 0;
CREATE INDEX idx_transactions_timestamp ON transactions(timestamp);
