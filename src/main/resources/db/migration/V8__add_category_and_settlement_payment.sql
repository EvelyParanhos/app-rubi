ALTER TABLE transactions ADD COLUMN category VARCHAR(50);
ALTER TABLE recurring_transactions ADD COLUMN category VARCHAR(50);
ALTER TABLE transaction_splits ADD COLUMN is_settled BOOLEAN DEFAULT FALSE;
ALTER TABLE transaction_splits ADD COLUMN settled_at TIMESTAMP;
