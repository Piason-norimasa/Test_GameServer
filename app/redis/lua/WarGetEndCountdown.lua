
local hgetall = function(key)
    local keyvalues = redis.call('hgetall', key)
    local result = {}

    for idx = 1, #keyvalues, 2 do
        result[keyvalues[idx]] = keyvalues[idx + 1]
    end
    return result
end

-- 抗争の時間終了チェック
local now_time = ARGV[1]
local war_time = hgetall(KEYS[1] .. 'time')

if now_time >= war_time['end'] then
    return cmsgpack.pack({ type = 'error', status = 'after_end' })
end

-- 抗争終了フラグチェック
local key_war_data = KEYS[1] .. 'war_data'
if redis.call('hget', key_war_data, 'is_end') ~= '0' then
    return cmsgpack.pack({ type = 'error', status = 'is_end' })
end

local key_war_data              = KEYS[1] .. 'war_data'
local war_end_countdown_data    = redis.call('hmget', key_war_data, 'is_end_countdown', 'countdown_start_time', 'win_team_id', 'lose_team_id')

return cmsgpack.pack({ type = 'ok', data = war_end_countdown_data })
