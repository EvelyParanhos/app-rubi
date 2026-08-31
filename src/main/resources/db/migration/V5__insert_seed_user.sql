INSERT INTO users (id, name, phone_number, pin_hash, is_active, created_at)
VALUES (
    'a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d',
    'Evelyn',
    '+5571993198981',
    '$2a$10$ohMofbCsHrJbo4QmhQlhQ.EZFn2hLhaoP1MEw6dkhPc9/rQg6iojG',
    TRUE,
    CURRENT_TIMESTAMP
) ON CONFLICT (phone_number) DO UPDATE SET pin_hash = EXCLUDED.pin_hash;
