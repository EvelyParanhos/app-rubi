-- V19__add_goal_amount_to_accounts.sql
-- Add goal_amount column to accounts table for per-pocket savings goals

ALTER TABLE accounts ADD COLUMN goal_amount DECIMAL(19, 4);
