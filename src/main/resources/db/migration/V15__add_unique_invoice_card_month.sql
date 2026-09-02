-- V15__add_unique_invoice_card_month.sql
-- Add unique constraint for credit_card_id + reference_month on invoices

ALTER TABLE invoices ADD CONSTRAINT uk_invoice_card_month UNIQUE (credit_card_id, reference_month);
