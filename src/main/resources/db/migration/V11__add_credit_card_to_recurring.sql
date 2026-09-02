-- V11__add_credit_card_to_recurring.sql
-- Migration to support recurring subscriptions linked directly to Credit Cards

ALTER TABLE recurring_transactions 
    ADD COLUMN credit_card_id UUID REFERENCES credit_cards(id),
    ALTER COLUMN account_id DROP NOT NULL;
