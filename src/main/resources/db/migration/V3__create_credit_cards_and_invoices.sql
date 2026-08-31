CREATE TABLE credit_cards (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    credit_limit DECIMAL(19,4) NOT NULL,
    closing_day INT NOT NULL,
    due_day INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_credit_cards_account FOREIGN KEY (account_id) REFERENCES accounts (id)
);

CREATE TABLE invoices (
    id UUID PRIMARY KEY,
    credit_card_id UUID NOT NULL,
    reference_month VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_invoices_credit_card FOREIGN KEY (credit_card_id) REFERENCES credit_cards (id)
);

ALTER TABLE transactions ADD COLUMN invoice_id UUID;
ALTER TABLE transactions ADD COLUMN installment_number INT;
ALTER TABLE transactions ADD COLUMN total_installments INT;

ALTER TABLE transactions ADD CONSTRAINT fk_transactions_invoice FOREIGN KEY (invoice_id) REFERENCES invoices (id);
