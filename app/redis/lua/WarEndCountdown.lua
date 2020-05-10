
-- 抗争終了フラグを更新
local key_war_data = KEYS[1] .. 'war_data'
redis.call('hmset', key_war_data, 'is_end_countdown', '2', 'is_end', '1')

return cmsgpack.pack({ type = 'ok'})
