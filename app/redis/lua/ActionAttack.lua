
-- redis Hashデータ取得用関数
local hgetall = function(key)

    local keyvalues = redis.call('hgetall', key)
    local result = {}
    for idx = 1, #keyvalues, 2 do
        result[keyvalues[idx]] = keyvalues[idx + 1]
    end

    return result
end

-- 全員死亡しているかどうかのチェック関数
local is_dead_all = function(check_team_id)

    local key = KEYS[1] .. check_team_id .. ':parent'
    local user_id_list = redis.call('smembers', key)
    for i, user_id in ipairs(user_id_list) do
        local key_user_data = KEYS[1] .. check_team_id .. ':' .. user_id
        if redis.call('hget', key_user_data, 'is_dead') == '0' then
            return false
        end
    end

    return true
end

-- スキルゲージを更新
local update_skill_gauge = function(team_id, user_id, action_type, action_id, action_hit, is_player_action)

    local key_user_data = KEYS[1] .. team_id .. ':' .. user_id

    if is_player_action and tonumber(action_type) == 10 then

        -- プレイヤーのスキル発動時
        local key_skill_gauge = 'skill' .. action_id .. '_gauge'
        local key_skill_level = 'skill' .. action_id .. '_level_max'
        local user_data = redis.call('hmget', key_user_data, key_skill_gauge, key_skill_level)
        local current_gauge = tonumber(user_data[1])

        -- スキル使用の場合は消費
        local skill_level = math.floor (current_gauge / 100)
        local next_gauge = tonumber(current_gauge) - skill_level * 100

        redis.call('hmset', key_user_data, key_skill_gauge, next_gauge)

    elseif tonumber(action_type) >= 0 then

        local key_skill_gauge       = 'skill1_gauge'
        local key_skill_level_max   = 'skill1_level_max'

        if is_player_action and action_hit == '1' then

            key_skill_gauge     = 'skill1_gauge'
            key_skill_level_max = 'skill1_level_max'
        elseif is_player_action and action_hit == '0' then
            key_skill_gauge     = 'skill2_gauge'
            key_skill_level_max = 'skill2_level_max'
        elseif is_player_action == false and action_hit == '1' then
            key_skill_gauge     = 'skill2_gauge'
            key_skill_level_max = 'skill2_level_max'
        elseif is_player_action == false and action_hit == '0' then
            key_skill_gauge     = 'skill3_gauge'
            key_skill_level_max = 'skill3_level_max'
        end

        local gauge_data = redis.call('hmget', key_user_data, key_skill_gauge, key_skill_level_max)

        -- 通常攻撃の場合は、action_idによってゲージ量を加算する
        local next_gauge = tonumber(gauge_data[1]) + 20
        local gauge_max = tonumber(gauge_data[2]) * 100
        if next_gauge > gauge_max then
            next_gauge = gauge_max
        end
        redis.call('hmset', key_user_data, key_skill_gauge, next_gauge)
    end

    return redis.call('hmget', key_user_data, 'skill1_gauge', 'skill2_gauge', 'skill3_gauge')
end

local now_turn_no       = ARGV[1]
local is_enemy_first    = ARGV[2]
local team_id           = ARGV[3]
local user_id           = ARGV[4]
local player_action_type = ARGV[5]
local player_action_id  = ARGV[6]
local player_action_hit  = ARGV[7]
local player_do_damage  = ARGV[8]
local enemy_team_id     = ARGV[9]
local enemy_user_id     = ARGV[10]
local enemy_action_type = ARGV[11]
local enemy_action_id   = ARGV[12]
local enemy_action_hit  = ARGV[13]
local enemy_do_damage   = ARGV[14]
local now_time          = ARGV[15]

local key_war_data      = KEYS[1] .. 'war_data'
local key_war_time      = KEYS[1] .. 'time'
local key_user_data     = KEYS[1] .. team_id .. ':' .. user_id
local key_enemy_data    = KEYS[1] .. enemy_team_id .. ':' .. enemy_user_id

-- 抗争の時間終了チェック
local war_time = hgetall(key_war_time)
if now_time >= war_time['end'] then
    return cmsgpack.pack({ type = 'error', status = 'after_end' })
end

-- 抗争終了フラグチェック
if redis.call('hget', key_war_data, 'is_end') == '1' then
    return cmsgpack.pack({ type = 'error', status = 'is_end' })
end

-- ユーザーの死亡状態チェック
if redis.call('hget', key_user_data, 'is_dead') == '1' then
    return cmsgpack.pack({ type = 'error', status = 'is_dead' })
end
if redis.call('hget', key_enemy_data, 'is_dead') == '1'  then
    return cmsgpack.pack({ type = 'error', status = 'is_dead' })
end

-- レスポンス用変数
local pl_is_dead = '0'
local em_is_dead = '0'
local pl_rest_hp = 0
local em_rest_hp = 0
local plteam_is_dead_all = false
local emteam_is_dead_all = false
local pl_skill_gauge = {}
local em_skill_gauge = {}

-- ターン数更新
redis.call('hmset', key_user_data, 'turn_number', now_turn_no)

-- ダメージによるHP更新, アクションタイプがスキルの場合は、スキルゲージを更新
if is_enemy_first == '1' then

    -- 敵先行でダメージを与える
    local pl_hp = redis.call('hget', key_user_data, 'hp')
    pl_rest_hp = pl_hp - enemy_do_damage
    if pl_rest_hp <= 0 then
        pl_rest_hp = 0
        pl_is_dead = '1'
        player_do_damage = 0
    end
    redis.call('hmset', key_user_data, 'hp', pl_rest_hp, 'is_dead', pl_is_dead)
    redis.call('hincrby', key_enemy_data, 'sum_damage', enemy_do_damage)

    -- スキルゲージ更新
    pl_skill_gauge = update_skill_gauge(team_id, user_id, enemy_action_type, enemy_action_id, enemy_action_hit, false)

    if pl_is_dead == '0' then

        local em_hp = redis.call('hget', key_enemy_data, 'hp')
        em_rest_hp = em_hp - player_do_damage
        if em_rest_hp <= 0 then
            em_rest_hp = 0
            em_is_dead = '1'
        end
        redis.call('hmset', key_enemy_data, 'hp', em_rest_hp, 'is_dead', em_is_dead)
        redis.call('hincrby', key_user_data, 'sum_damage', player_do_damage)

        -- スキルゲージ更新
        pl_skill_gauge = update_skill_gauge(team_id, user_id, player_action_type, player_action_id, player_action_hit, true)
    else
        em_rest_hp = redis.call('hget', key_enemy_data, 'hp')
    end
else

    -- プレイヤー先行でダメージを与える
    local em_hp = redis.call('hget', key_enemy_data, 'hp')
    em_rest_hp = em_hp - player_do_damage
    if em_rest_hp <= 0 then
        em_rest_hp = 0
        em_is_dead = '1'
        enemy_do_damage = 0
    end
    redis.call('hmset', key_enemy_data, 'hp', em_rest_hp, 'is_dead', em_is_dead)
    redis.call('hincrby', key_user_data, 'sum_damage', player_do_damage)

    -- スキルゲージ更新
    pl_skill_gauge = update_skill_gauge(team_id, user_id, player_action_type, player_action_id, player_action_hit, true)

    if em_is_dead == '0' then

        local pl_hp = redis.call('hget', key_user_data, 'hp')
        pl_rest_hp = pl_hp - enemy_do_damage
        if pl_rest_hp <= 0 then
            pl_rest_hp = 0
            pl_is_dead = '1'
        end
        redis.call('hmset', key_user_data, 'hp', pl_rest_hp, 'is_dead', pl_is_dead)
        redis.call('hincrby', key_enemy_data, 'sum_damage', enemy_do_damage)

        -- スキルゲージ更新
        pl_skill_gauge = update_skill_gauge(team_id, user_id, enemy_action_type, enemy_action_id, enemy_action_hit, false)
    else
        pl_rest_hp = redis.call('hget', key_user_data, 'hp')
    end
end

-- チーム全員死亡チェック
plteam_is_dead_all = is_dead_all(team_id)
emteam_is_dead_all = is_dead_all(enemy_team_id)

-- 既に全員死亡でカウントダウン中かチェック
local is_start_countdown = false
local is_notify_countdown = false
if redis.call('hget', key_war_data, 'is_end_countdown') == '1' then
    is_start_countdown = true
end

-- チーム全員死亡時の場合は決着カウントダウンの時間設定を行う
if is_start_countdown == false and plteam_is_dead_all == true then

    is_notify_countdown = true
    redis.call('hmset', key_war_data, 'is_end_countdown', '1', 'countdown_start_time', now_time, 'win_team_id', enemy_team_id, 'lose_team_id', team_id)
elseif is_start_countdown == false and emteam_is_dead_all == true then

    is_notify_countdown = true
    redis.call('hmset', key_war_data, 'is_end_countdown', '1', 'countdown_start_time', now_time, 'win_team_id', team_id, 'lose_team_id', enemy_team_id)
end

-- 返却
return cmsgpack.pack({ type = 'ok',
                        player_is_dead      = pl_is_dead,
                        player_rest_hp      = pl_rest_hp,
                        player_do_damage    = player_do_damage,
                        player_skill_gauge  = pl_skill_gauge,
                        enemy_is_dead       = em_is_dead,
                        enemy_rest_hp       = em_rest_hp,
                        enemy_do_damage     = enemy_do_damage,
                        enemy_skill_gauge   = em_skill_gauge,
                        plteam_is_dead_all  = plteam_is_dead_all,
                        emteam_is_dead_all  = emteam_is_dead_all,
                        is_notify_countdown = is_notify_countdown
                    })
