CREATE TABLE recurring_expenses (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(19,4) NOT NULL,
    type VARCHAR(50) NOT NULL,
    due_day INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_recurring_account FOREIGN KEY (account_id) REFERENCES accounts (id)
);

ALTER TABLE transactions ADD COLUMN status VARCHAR(50) DEFAULT 'CONFIRMED';
ALTER TABLE transactions ADD COLUMN recurring_expense_id UUID;
ALTER TABLE transactions ADD CONSTRAINT fk_transactions_recurring FOREIGN KEY (recurring_expense_id) REFERENCES recurring_expenses (id);
