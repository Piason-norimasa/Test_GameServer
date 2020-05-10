
-- 抗争終了フラグチェック
local key_war_data = KEYS[1] .. 'war_data'
if redis.call('hget', key_war_data, 'is_end') ~= '0' then
    return cmsgpack.pack({ type = 'error', status = 'is_end' })
end

local user_id           = ARGV[1]
local team_id           = ARGV[2]
local expire_time       = ARGV[3]
local key_team          = KEYS[1] .. team_id .. ':'
local key_team_user     = key_team .. user_id

-- ターゲット状態を解除する
redis.call('hmset', key_team_user, 'target_user_id', 0)
redis.call('hmset', key_team_user, 'turn_number', 0)

return cmsgpack.pack({})
