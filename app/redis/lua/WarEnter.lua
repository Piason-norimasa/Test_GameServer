
local hgetall = function(key)
    local keyvalues = redis.call('hgetall', key)
    local result = {}

    for idx = 1, #keyvalues, 2 do
        result[keyvalues[idx]] = keyvalues[idx + 1]
    end
    return result
end

-- 抗争の時間終了チェック
local now_time = ARGV[3]
local war_time = hgetall(KEYS[1] .. 'time')

if now_time >= war_time['end'] then
    return cmsgpack.pack({ type = 'error', status = 'after_end' })
end

-- 抗争終了フラグチェック
local key_war_data = KEYS[1] .. 'war_data'
if redis.call('hget', key_war_data, 'is_end') ~= '0' then
    return cmsgpack.pack({ type = 'error', status = 'is_end' })
end

local team_id           = ARGV[1]
local user_id           = ARGV[2]
local key_client        = KEYS[1] .. 'client:' .. team_id
local key_enemy_team    = KEYS[1] .. 'enemy:' .. team_id
local expire_time       = ARGV[4]

-- 抗争に参加したユーザーIDを登録
redis.call('sadd', key_client, user_id)
redis.call('expire', key_client, expire_time)

local key_war_data      = KEYS[1] .. 'war_data'
local key_war_time      = KEYS[1] .. 'time'
local war_end_countdown_data    = redis.call('hmget', key_war_data, 'is_end_countdown', 'countdown_start_time', 'win_team_id', 'lose_team_id')
local enemy_team_id             = redis.call('get', key_enemy_team)

return cmsgpack.pack({ type = 'ok', start_time = war_time['start'], end_time = war_time['end'], enemy_team_id = enemy_team_id, countdown_data = war_end_countdown_data })
