-- Épico 2: Expandir modelagem para partidas dobradas, custodian_id, recurring_transactions e restrição única de parceria ativa

ALTER TABLE accounts ADD COLUMN custodian_id UUID;
UPDATE accounts SET custodian_id = owner_id WHERE custodian_id IS NULL;

ALTER TABLE transactions ADD COLUMN source_account_id UUID;
ALTER TABLE transactions ADD COLUMN dest_account_id UUID;

ALTER TABLE transactions ADD CONSTRAINT fk_transactions_source_acc FOREIGN KEY (source_account_id) REFERENCES accounts (id);
ALTER TABLE transactions ADD CONSTRAINT fk_transactions_dest_acc FOREIGN KEY (dest_account_id) REFERENCES accounts (id);

ALTER TABLE recurring_expenses RENAME TO recurring_transactions;

-- Índice parcial único para impedir múltiplos vínculos de parceria ACTIVE simultâneos (RN02 / Épico 2.1)
CREATE UNIQUE INDEX idx_unique_active_user1 ON partnerships (user_1_id) WHERE status = 'ACTIVE';
CREATE UNIQUE INDEX idx_unique_active_user2 ON partnerships (user_2_id) WHERE status = 'ACTIVE';
