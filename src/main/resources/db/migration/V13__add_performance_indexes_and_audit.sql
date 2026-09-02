-- V13__add_performance_indexes_and_audit.sql
-- Migration for high performance composite indexes and audit logging

-- Composite performance indexes
CREATE INDEX IF NOT EXISTS idx_tx_acc_date_cat ON transactions (account_id, reference_date, category);
CREATE INDEX IF NOT EXISTS idx_tx_invoice_type ON transactions (invoice_id, type);
CREATE INDEX IF NOT EXISTS idx_rec_acc_active ON recurring_transactions (account_id, is_active);
CREATE INDEX IF NOT EXISTS idx_rec_card_active ON recurring_transactions (credit_card_id, is_active);
CREATE INDEX IF NOT EXISTS idx_invoices_card_month ON invoices (credit_card_id, reference_month);

-- Audit Log table for sensitive actions and DLQ alerts
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY,
    user_id UUID,
    entity_name VARCHAR(100) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_user_entity ON audit_logs (user_id, entity_name);
