CREATE TABLE users (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(100) UNIQUE NOT NULL,
    pin_hash VARCHAR(255) NOT NULL,
    telegram_chat_id VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL
);

CREATE TABLE partnerships (
    id UUID PRIMARY KEY,
    user_1_id UUID NOT NULL,
    user_2_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT fk_user_1 FOREIGN KEY (user_1_id) REFERENCES users (id),
    CONSTRAINT fk_user_2 FOREIGN KEY (user_2_id) REFERENCES users (id)
);
