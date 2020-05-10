
-- 要素をすべて取得
local hgetall = function(key)
    local keyvalues = redis.call('hgetall', key)
    local result = {}

    for idx = 1, #keyvalues, 2 do
        result[keyvalues[idx]] = keyvalues[idx + 1]
    end
    return result
end

local team_id           = ARGV[1]
local user_id           = ARGV[2]
local target_user_id    = ARGV[3]
local item_mst_id       = ARGV[4]
local item_category_id  = ARGV[5]
local now_time          = ARGV[6]

local key_team          = KEYS[1] .. team_id .. ':'

-- 抗争の時間終了チェック
local war_time = hgetall(KEYS[1] .. 'time')
if now_time >= war_time['end'] then
    return cmsgpack.pack({ type = 'error', status = 'after_end' })
end

-- 抗争終了フラグチェック
local key_war_data = KEYS[1] .. 'war_data'
if redis.call('hget', key_war_data, 'is_end') ~= '0' then
    return cmsgpack.pack({ type = 'error', status = 'is_end' })
end

-- ターゲットユーザーの生存チェック
local is_dead = redis.call('hget', (key_team .. target_user_id), 'is_dead')
if is_dead == '0' then

    return cmsgpack.pack({ type = 'error', status = 'dead' })
else

    -- 体力を全回復させる
    local hp_data = redis.call('hmget', (key_team .. target_user_id), 'hp', 'hp_max')
    redis.call('hmset', (key_team .. target_user_id), 'is_dead', '0')
    redis.call('hmset', (key_team .. target_user_id), 'hp', hp_data[2])

    -- 決着フラグをクリア
    if team_id == redis.call('hget', key_war_data, 'lose_team_id') then
        redis.call('hmset', key_war_data, 'is_end_countdown', '0', 'countdown_start_time', 0, 'win_team_id', 0, 'lose_team_id', 0)
    end

    -- 貢献度情報としてredisに使用した情報を登録(DB Logに書き込むだけで良い？)
    local key_save = 'item' .. item_category_id .. '_use_num'
    redis.call('hincrby', (key_team .. user_id), key_save, 1)

    return cmsgpack.pack({ type = 'ok', status = 'ok', heal_value = (hp_data[2] - hp_data[1]), rest_hp = hp_data[2] })
end
