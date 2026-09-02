-- V12__create_category_budgets_and_goals.sql
-- Migration to create category budgets (spending limits) and goals table

CREATE TABLE category_budgets (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL REFERENCES users(id),
    category VARCHAR(50) NOT NULL,
    monthly_limit DECIMAL(19, 4),
    monthly_goal DECIMAL(19, 4),
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT uk_owner_category UNIQUE (owner_id, category)
);
