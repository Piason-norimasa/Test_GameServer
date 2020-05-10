
-- データをすべて取得
local hgetall = function(key)
    local keyvalues = redis.call('hgetall', key)
    local result = {}

    for idx = 1, #keyvalues, 2 do
        result[keyvalues[idx]] = keyvalues[idx + 1]
    end
    return result
end

-- target_user_idをロック中のユーザーリストを取得
local get_is_target_user_list = function(team_id, target_user_id)
    
    if tonumber(target_user_id) <= 0 then
        return {}
    end

    local result_list = {}
    local key = KEYS[1] .. team_id .. ':parent'
    local user_id_list = redis.call('smembers', key)

    for i, id in ipairs(user_id_list) do

        local key_user_data = KEYS[1] .. team_id .. ':' .. id
        local target_data = redis.call('hmget', key_user_data, 'target_user_id', 'target_lock_time')

        if tonumber(target_data[1]) == tonumber(target_user_id) then
            local attacker = {}
            attacker['user_id'] = id
            attacker['target_lock_time'] = target_data[2]
            table.insert(result_list, attacker)
        end
    end

    return result_list
end


local team_id           = ARGV[1]
local key_enemy_team    = KEYS[1] .. 'enemy:' .. team_id
local key_team          = KEYS[1] .. team_id .. ':'
local enemy_team_id     = redis.call('get', key_enemy_team)

local user_id           = ARGV[2]
local user_name         = ARGV[3]
local enemy_user_id     = ARGV[4]
local now_time          = ARGV[5]
local expire_time       = ARGV[6]
local key_team_user     = key_team .. user_id
local key_enemy         = KEYS[1] .. enemy_team_id .. ':'
local key_enemy_user    = key_enemy .. enemy_user_id
local war_time          = hgetall(KEYS[1] .. 'time')
local key_target_list   = key_team .. 'target'

-- 開始時間チェック
if tonumber(now_time) < tonumber(war_time['start']) - 60 then
    return cmsgpack.pack({ status = 'before_start' })
end

-- 敵ユーザーデータ存在チェック
if redis.call('exists', key_enemy_user) == '0' then
    return cmsgpack.pack({ status = 'is_dead'})
end

-- 敵の生存チェック
if redis.call('hget', key_enemy_user, 'is_dead') == '1' then
    return cmsgpack.pack({ status = 'is_dead'})
end

local current_target_id = redis.call('hget', key_team_user, 'target_user_id')

-- 攻撃対象ユーザーIDをセットし、ターン数を初期化
redis.call('hmset', key_team_user, 'target_user_id', enemy_user_id, 'target_lock_time', now_time, 'turn_number', 0)

-- 変更になったユーザーIDリストを取得
local before_target_data = {}
before_target_data['user_id']        = current_target_id
before_target_data['have_enemy_ids'] = get_is_target_user_list(team_id, current_target_id)

local after_target_data = {}
after_target_data['user_id']         = enemy_user_id
after_target_data['have_enemy_ids']  = get_is_target_user_list(team_id, enemy_user_id)

return cmsgpack.pack({ status = 'ok', before_enemy = before_target_data, after_enemy = after_target_data})
