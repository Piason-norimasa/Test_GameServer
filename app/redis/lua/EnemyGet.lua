
local hgetall = function(key)
    local keyvalues = redis.call('hgetall', key)
    local result = {}

    for idx = 1, #keyvalues, 2 do
        result[keyvalues[idx]] = keyvalues[idx + 1]
    end
    return result
end

local now_time = ARGV[2]
local war_time = hgetall(KEYS[1] .. 'time')

-- 抗争時間登録チェック
if not war_time['start'] or not war_time['end'] then
    return cmsgpack.pack({ type = 'error', status = 'nothing_data' })
end

-- 抗争開始時間チェック
if tonumber(now_time) + 60 * 2 <= tonumber(war_time['start']) then
    return cmsgpack.pack({ type = 'error', status = 'after_end' })
end

-- 抗争終了時間チェック
if tonumber(now_time) >= tonumber(war_time['end']) then
    return cmsgpack.pack({ type = 'error', status = 'after_end' })
end

-- 抗争終了フラグチェック
local key_war_data = KEYS[1] .. 'war_data'
if redis.call('hget', key_war_data, 'is_end') ~= '0' then
    return cmsgpack.pack({ type = 'error', status = 'is_end' })
end

local team_id           = ARGV[1]
local key_team          = KEYS[1] .. 'enemy:' .. team_id
local enemy_team_id     = redis.call('get', key_team)

local key_my_team       = KEYS[1] .. team_id .. ':'
local key_enemy_team    = KEYS[1] .. enemy_team_id .. ':'
local parent_members    = redis.call('smembers', key_enemy_team .. 'parent')

local parent_data = {}
for k, v in ipairs(parent_members) do
    table.insert(parent_data, hgetall(key_enemy_team .. v))
end

return cmsgpack.pack({ type = 'ok', data = { parent = parent_data }})
