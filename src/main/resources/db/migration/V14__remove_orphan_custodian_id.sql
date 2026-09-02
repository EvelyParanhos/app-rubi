-- V14__remove_orphan_custodian_id.sql
-- Remove orphan custodian_id column from accounts table

ALTER TABLE accounts DROP COLUMN IF EXISTS custodian_id;
