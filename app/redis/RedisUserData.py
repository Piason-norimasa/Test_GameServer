#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import define, options

from redis import Redis, ConnectionPool
from RedisBaseData import RedisBaseData
import msgpack, math, json
from datetime import timedelta, datetime

from Define import ActionType
from Utility import get_serial_date

class RedisUserData(RedisBaseData):

    def __init__(self, connection_pool = None):

        super(RedisUserData, self).__init__(connection_pool)

    # 現在のターンを取得する #### todo:: ※redisにて管理。他の対戦相手を選んだ時に初期化する
    def get_now_turn_number(self, war_id, team_id, user_id):

        key = '{0}:'.format(war_id) + str(team_id) + ':' + str(user_id)
        number = self._redis.hget(key, 'turn_number')

        return int(number)

    # ユーザーのステータス情報を取得する
    def get_user_status(self, war_id, team_id, user_id):

        key = '{0}:'.format(war_id) + str(team_id) + ':' + str(user_id)

        atk, deffence, agi, atk_bike, def_bike, agi_bike, atk_avatar, def_avatar, agi_avatar, atk_effect, def_effect, agi_effect, co_pl_atk, co_pl_def, co_pl_agi, co_em_atk, co_em_def, co_em_agi = self._redis.hmget(key, 'atk', 'def', 'agi', 'atk_bike', 'def_bike', 'agi_bike', 'atk_avatar', 'def_avatar', 'agi_avatar', 'atk_effect', 'def_effect', 'agi_effect', 'co_player_atk', 'co_player_def', 'co_player_agi', 'co_enemy_atk', 'co_enemy_def', 'co_enemy_agi' )

        status = {}
        status['atk'] = int(atk) + int(atk_bike) + int(atk_avatar) + int(atk_effect)
        status['def'] = int(deffence) + int(def_bike) + int(def_avatar) + int(def_effect)
        status['agi'] = int(agi) + int(agi_bike) + int(agi_avatar) + int(agi_effect)
        status['base_atk'] = int(atk)
        status['base_def'] = int(deffence)
        status['base_agi'] = int(agi)

        # 自分自信への特効効果追加
        status['player_atk'] = float(co_pl_atk)
        status['player_def'] = float(co_pl_def)
        status['player_agi'] = float(co_pl_agi)
        status['enemy_atk'] = float(co_em_atk)
        status['enemy_def'] = float(co_em_def)
        status['enemy_agi'] = float(co_em_agi)

        return status

    # ユーザーHP情報を更新する
    def get_user_hp(self, war_id, team_id, user_id):

        key = '{0}:'.format(war_id) + str(team_id) + ':' + str(user_id)
        hp_data = self._redis.hmget(key, 'hp', 'hp_max')

        return { 'hp':int(float(hp_data[0])), 'hp_max':int(float(hp_data[1])) }

    # 敵の行動パターンロジック情報を取得する
    def get_enemy_logic_data(self, user_id):

        return []

    # スキル発動可能なレベルを取得
    def get_enable_skill_level(self, war_id, team_id, user_id, skill_id):

        # TODO: 他人の行動によってskill_guage の変動はないので取得部分を lua で書く必要ない？？？
        key = '{0}:'.format(war_id) + str(team_id) + ':' + str(user_id)
        key_skill_gauge = 'skill' + str(skill_id) + '_gauge'
        skill_gauge = self._redis.hget(key, key_skill_gauge)

        return math.floor(int(skill_gauge) / 100)

    # アイテムの使用状況の情報を取得
    def get_item_data_info(self, war_id, team_id, user_id):

        key = '{0}:'.format(war_id) + str(team_id) + ':' + str(user_id)
        item_info = self._redis.hmget(key, 'item0_use_num', 'item0_use_num_limit', 'item1_use_num', 'item1_use_num_limit', 'item4_use_num', 'item4_use_num_limit')

        # 使いやすいように加工
        ret_item_info_list = {}
        # small 
        item_data                   = {}
        item_data['use_num']        = item_info[0]
        item_data['use_num_limit']  = item_info[1]
        ret_item_info_list[0]       = item_data

        # big
        item_data                   = {}
        item_data['use_num']        = item_info[2]
        item_data['use_num_limit']  = item_info[3]
        ret_item_info_list[1]       = item_data

        # aed
        item_data                   = {}
        item_data['use_num']        = item_info[4]
        item_data['use_num_limit']  = item_info[5]
        ret_item_info_list[4]       = item_data

        return ret_item_info_list

    def get_user_contribution(self, war_id, team_id, user_id):

        # TODO: 他人の行動によってskill_guage の変動はないので取得部分を lua で書く必要ない？？？
        key = '{0}:'.format(war_id) + str(team_id) + ':' + str(user_id)

        contribution = {}
        contribution['sum_do_damage']   = int(self._redis.hget(key, 'sum_damage'))
        contribution['use_item']        = json.dumps(self.get_item_data_info(war_id, team_id, user_id))

        return contribution

    # ユーザーのHPを更新
    def update_user_data(self, 
                            war_id, 
                            now_turn_number, 
                            is_enemy_first, 
                            team_id, 
                            user_id, 
                            player_action_type, 
                            player_action_id,
                            player_action_hit,
                            player_do_damage, 
                            enemy_team_id, 
                            enemy_user_id, 
                            enemy_action_type, 
                            enemy_action_id,
                            enemy_action_hit,
                            enemy_do_damage):

        key = '{0}:'.format(war_id)
        sha = 'kkkkfd3b3977c7441783f258c322e0616c2835b'
        lua_file_name = 'ActionAttack.lua'
        sha = self._load_lua_script(lua_file_name, sha)

        result = msgpack.unpackb(self._redis.evalsha(sha, 1, key,
                                                    now_turn_number, 
                                                    is_enemy_first, 
                                                    team_id, 
                                                    user_id, 
                                                    int(player_action_type),
                                                    int(player_action_id),
                                                    int(player_action_hit), 
                                                    int(player_do_damage), 
                                                    enemy_team_id,
                                                    enemy_user_id, 
                                                    int(enemy_action_type),
                                                    int(enemy_action_id),
                                                    int(enemy_action_hit),
                                                    int(enemy_do_damage), 
                                                    get_serial_date()))


        return result


    # ターゲットユーザーに対して アイテムを使用する
    def use_item(self, war_id, team_id, user_id, item_category, use_item_id, item_category_id, target_id, heal_effect):

        if item_category == ActionType.use_item_hp_heal:

            key = '{0}:'.format(war_id)
            sha = 'aaaaafd3b3977c7441783f258c322e0616c2835b'
            lua_file_name = 'ItemUseHpHeal.lua'
            sha = self._load_lua_script(lua_file_name, sha)

            return msgpack.unpackb(self._redis.evalsha(sha, 1, key, team_id, user_id, target_id, heal_effect, use_item_id, item_category_id, get_serial_date()))

        elif item_category == ActionType.use_item_dead_heal:

            key = '{0}:'.format(war_id)
            sha = 'bbbbafd3b3977c7441783f258c322e0616c2835b'
            lua_file_name = 'ItemUseAed.lua'
            sha = self._load_lua_script(lua_file_name, sha)

            return msgpack.unpackb(self._redis.evalsha(sha, 1, key, team_id, user_id, target_id, use_item_id, item_category_id, get_serial_date()))

        elif item_category == ActionType.use_item_skill_heal:
            pass
