-- V16__standardize_reference_month.sql
-- Standardize reference_month column to VARCHAR(7) with YYYY-MM format check constraints

ALTER TABLE invoices ALTER COLUMN reference_month TYPE VARCHAR(7);
ALTER TABLE invoices ADD CONSTRAINT chk_invoice_ref_month_format CHECK (reference_month ~ '^\d{4}-\d{2}$');
ALTER TABLE recurring_fulfillments ADD CONSTRAINT chk_fulfill_ref_month_format CHECK (reference_month ~ '^\d{4}-\d{2}$');
ALTER TABLE recurring_overrides ADD CONSTRAINT chk_override_ref_month_format CHECK (reference_month ~ '^\d{4}-\d{2}$');
