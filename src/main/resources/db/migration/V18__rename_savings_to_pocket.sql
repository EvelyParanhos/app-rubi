-- V18__rename_savings_to_pocket.sql
-- Rename SAVINGS account type to POCKET for Caixinhas/Reserves

UPDATE accounts SET type = 'POCKET' WHERE type = 'SAVINGS';
