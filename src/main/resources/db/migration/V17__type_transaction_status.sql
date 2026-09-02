-- V17__type_transaction_status.sql
-- Constrain transaction status values to PENDING, CONFIRMED, CANCELED

ALTER TABLE transactions ADD CONSTRAINT chk_transaction_status
    CHECK (status IN ('PENDING', 'CONFIRMED', 'CANCELED'));
