CREATE TABLE transaction_splits (
    id UUID PRIMARY KEY,
    transaction_id UUID NOT NULL,
    creditor_id UUID NOT NULL,
    debtor_id UUID NOT NULL,
    amount DECIMAL(19,4) NOT NULL,
    status VARCHAR(50) NOT NULL,
    reference_month VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_splits_transaction FOREIGN KEY (transaction_id) REFERENCES transactions (id),
    CONSTRAINT fk_splits_creditor FOREIGN KEY (creditor_id) REFERENCES users (id),
    CONSTRAINT fk_splits_debtor FOREIGN KEY (debtor_id) REFERENCES users (id)
);
