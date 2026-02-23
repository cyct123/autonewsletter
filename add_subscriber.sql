-- Quick SQL script to add a test subscriber
-- Run this in WSL2 with: docker-compose exec db psql -U autonews -d autonews -f add_subscriber.sql

-- Example 1: Add PushPlus subscriber
-- Replace 'your_pushplus_token' with your actual token from https://www.pushplus.plus
INSERT INTO subscribers (id, identifier, channel_type, active, preferences, created_at, updated_at)
VALUES (
    gen_random_uuid(),
    'your_pushplus_token',
    'pushplus',
    true,
    '{"maxItemsPerNewsletter": 10}'::jsonb,
    NOW(),
    NOW()
) ON CONFLICT (identifier) DO NOTHING;

-- Example 2: Add WeChat webhook subscriber
-- Uncomment and replace with your WeChat webhook URL
-- INSERT INTO subscribers (id, identifier, channel_type, active, preferences, created_at, updated_at)
-- VALUES (
--     gen_random_uuid(),
--     'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY',
--     'wechat',
--     true,
--     '{"maxItemsPerNewsletter": 10}'::jsonb,
--     NOW(),
--     NOW()
-- ) ON CONFLICT (identifier) DO NOTHING;

-- Example 3: Add email subscriber
-- Uncomment and replace with your email address
-- INSERT INTO subscribers (id, identifier, channel_type, active, preferences, created_at, updated_at)
-- VALUES (
--     gen_random_uuid(),
--     'your_email@example.com',
--     'email',
--     true,
--     '{"maxItemsPerNewsletter": 10}'::jsonb,
--     NOW(),
--     NOW()
-- ) ON CONFLICT (identifier) DO NOTHING;

-- Verify subscribers were added
SELECT id, identifier, channel_type, active, preferences FROM subscribers;
