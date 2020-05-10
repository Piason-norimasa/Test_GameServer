
-- チームが与えた合計ダメージ数
local get_damage = function(team_id)

    local key_team = KEYS[1] .. team_id .. ':'
    local key_parent = key_team .. 'parent'

    local damage = redis.call('get', key_team .. 'damage')
    local parent_members = redis.call('smembers', key_parent)

    local ret_data = {}
    ret_data['hp']      = 0
    ret_data['hp_max']  = 0
    for k, v in ipairs(parent_members) do

        local data = redis.call('hmget', key_team .. v, 'hp', 'hp_max')
        ret_data['hp'] = ret_data['hp'] + tonumber(data[1])
        ret_data['hp_max'] = ret_data['hp_max'] + tonumber(data[2])
    end

    return ret_data
end

local end_process = function(key_end, key_end_result, win_team_id, lose_team_id, enemy_count, expire_time)

    redis.call('setex', key_end, expire_time, '2')
    redis.call('hmset', key_end_result, 'win', win_team_id, 'lose', lose_team_id, 'enemy_count', enemy_count, 'finish_attack', '0')
    redis.call('expire', key_end_result, expire_time)

    return cmsgpack.pack({ type = 'timeup', win = win_team_id, lose = lose_team_id, enemy_count = enemy_count, finish_attack = '0' })
end

-- 抗争の終了フラグチェック
local key_end           = KEYS[1] .. 'is_end'
local key_end_result    = KEYS[1] .. 'end_result'
if redis.call('get', key_end) == '2' then

    local data = redis.call('hmget', key_end_result, 'win', 'lose', 'enemy_count', 'finish_attack')
    return cmsgpack.pack({ type = 'is_end', win = data[1], lose = data[2], enemy_count = data[3], finish_attack = data[4] })
end

-- 抗争終了のカウントダウン時間中かチェック
local key_war_data              = KEYS[1] .. 'war_data'
local war_end_countdown_data    = redis.call('hmget', key_war_data, 'is_end_countdown', 'countdown_start_time', 'win_team_id', 'lose_team_id')
if war_end_countdown_data[1] == '1' then

    return end_process(key_end, key_end_result, war_end_countdown_data[3], war_end_countdown_data[4], 0, ARGV[3])
end

-- 勢力情報から勝利チームを算出
local my_team_hp    = get_damage(ARGV[1])
local enemy_team_hp = get_damage(ARGV[2])
local my_team_hp_ratio = my_team_hp['hp'] / my_team_hp['hp_max']
local enemy_team_hp_ratio = enemy_team_hp['hp'] / enemy_team_hp['hp_max']

-- (優先度1) 残りHPの割合から勝敗を算出
if my_team_hp_ratio < enemy_team_hp_ratio then

    return end_process(key_end, key_end_result, ARGV[2], ARGV[1], 0, ARGV[3])
elseif my_team_hp_ratio > enemy_team_hp_ratio then
    
    return end_process(key_end, key_end_result, ARGV[1], ARGV[2], 0, ARGV[3])
end

-- (優先度2) 残りHPの絶対値から勝敗を算出
if my_team_hp['hp'] > enemy_team_hp['hp'] then

    return end_process(key_end, key_end_result, ARGV[1], ARGV[2], 0, ARGV[3])
elseif my_team_hp['hp'] < enemy_team_hp['hp'] then

    return end_process(key_end, key_end_result, ARGV[2], ARGV[1], 0, ARGV[3])
end

-- (優先度3) ランダム抽選
if ARGV[4] == '1' then
    return end_process(key_end, key_end_result, ARGV[1], ARGV[2], 0, ARGV[3])
else
    return end_process(key_end, key_end_result, ARGV[2], ARGV[1], 0, ARGV[3])
end
