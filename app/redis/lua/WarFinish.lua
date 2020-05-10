
-- 抗争データの削除
local key_end       = KEYS[1]
local expire_time   = ARGV[1]

redis.call('setex', key_end, expire_time, '2')
