-- V21__add_target_amount_and_date_to_accounts.sql
-- Add target_amount and target_date columns to accounts table for Caixinhas target goals with/without deadline

ALTER TABLE accounts ADD COLUMN target_amount DECIMAL(19, 4) NULL;
ALTER TABLE accounts ADD COLUMN target_date DATE NULL;
