CREATE TABLE accounts (
    id UUID PRIMARY KEY,
    owner_id UUID NOT NULL,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL,
    is_joint BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_accounts_owner FOREIGN KEY (owner_id) REFERENCES users (id)
);

CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    account_id UUID NOT NULL,
    amount DECIMAL(19,4) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description VARCHAR(255),
    reference_date TIMESTAMP NOT NULL,
    CONSTRAINT fk_transactions_account FOREIGN KEY (account_id) REFERENCES accounts (id)
);
