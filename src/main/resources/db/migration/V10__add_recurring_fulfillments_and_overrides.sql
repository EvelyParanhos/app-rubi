-- V10__add_recurring_fulfillments_and_overrides.sql
-- Migration to support monthly fulfillments (checkoff) and overrides for recurring transactions

CREATE TABLE recurring_fulfillments (
    id UUID PRIMARY KEY,
    recurring_transaction_id UUID NOT NULL REFERENCES recurring_transactions(id),
    transaction_id UUID NOT NULL REFERENCES transactions(id),
    reference_month VARCHAR(7) NOT NULL,
    fulfilled_at TIMESTAMP NOT NULL,
    CONSTRAINT uk_rec_fulfill_month UNIQUE (recurring_transaction_id, reference_month)
);

CREATE TABLE recurring_overrides (
    id UUID PRIMARY KEY,
    recurring_transaction_id UUID NOT NULL REFERENCES recurring_transactions(id),
    reference_month VARCHAR(7) NOT NULL,
    override_amount DECIMAL(19, 4) NOT NULL,
    override_due_day INTEGER,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT uk_rec_override_month UNIQUE (recurring_transaction_id, reference_month)
);
