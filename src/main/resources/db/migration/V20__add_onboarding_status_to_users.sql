-- V20__add_onboarding_status_to_users.sql
-- Add onboarding_completed_at timestamp column to users table

ALTER TABLE users ADD COLUMN onboarding_completed_at TIMESTAMP NULL;
