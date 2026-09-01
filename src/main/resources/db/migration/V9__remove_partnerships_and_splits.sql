-- V9__remove_partnerships_and_splits.sql
-- Migration to remove partnerships, transaction splits and joint account flags for individual granularity model

DROP TABLE IF EXISTS transaction_splits CASCADE;
DROP TABLE IF EXISTS partnerships CASCADE;

ALTER TABLE accounts DROP COLUMN IF EXISTS is_joint;
