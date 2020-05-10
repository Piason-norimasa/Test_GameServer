#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import options

from PacketBase import Packet, PacketHandler
from WarResultLogic import WarResultLogic
from RedisUserData import RedisUserData

from Define import ActionType, BattleSkillType, END_COUNTDOWN_TIME
import random, math
from Utility import get_serial_date

BATTLE_LOGIC_HIT_RATE_MIN               = 0.4
BATTLE_LOGIC_HIT_RATE_MAX               = 0.95
BATTLE_LOGIC_HIT_RATE_DEFAULT           = 0.75
BATTLE_LOGIC_HIT_RATE_CONST             = 0.4
BATTLE_LOGIC_BASE_CRITICAL_RATE_ATK     = 0.1
BATTLE_LOGIC_BASE_CRITICAL_RATE_DEF     = 0.01

BATTLE_LOGIC_CRITICAL_RATE_THRESHOLD    = 1.0
BATTLE_LOGIC_CRITICAL_COEF_ATK_UPPER    = 1.5
BATTLE_LOGIC_CRITICAL_COEF_ATK_LOWER    = 1.1
BATTLE_LOGIC_CRITICAL_COEF_DEF_UPPER    = 1.5
BATTLE_LOGIC_CRITICAL_COEF_DEF_LOWER    = 1.1

BATTLE_LOGIC_ATK_COEF                   = 0.9
BATTLE_LOGIC_DEF_COEF                   = 0.7
BATTLE_LOGIC_DMG_COEF                   = 0.9
BATTLE_LOGIC_DAMAGE_FLUCTUATION_RANGE_UPPER = 1.2
BATTLE_LOGIC_DAMAGE_FLUCTUATION_RANGE_LOWER = 0.8
BATTLE_LOGIC_MAX_DAMAGE                 = 7777

class PacketAction(Packet):

    _hash_src = 'wsm'

    def __init__(self, data):
        
        self.enemy_user_id = int(data['enemy_user_id'])
        self.act_type   = int(data['act_type'])     # 行動種別(0:通常攻撃, 10:スキル攻撃, 20:回復アイテム, 21:気絶回復アイテム)
        self.target_id  = int(data['target_id'])    # 行動の対象となるユーザーID
        self.skill_id   = int(data['skill_id'])     # スキルID
        self._hash_code = str(data['code'])

    def _create_data_hash(self):

        hash_value = self._hash_src
        hash_value += str(self.enemy_user_id)
        hash_value += str(self.act_type)
        hash_value += str(self.target_id)
        hash_value += str(self.skill_id)

        return super(PacketAction, self)._create_data_hash(hash_value)


class PacketActionHandler(PacketHandler):

    def __init__(self, socket_handler, data):

        super(PacketActionHandler, self).__init__(socket_handler, data)

    def _execute(self):

        # リクエストパラメーターチェック
        packet = PacketAction(self._data)
        if not packet.is_validate_hash():
            return False

        #######################################################################
        user_id       = self._socket_handler._user_id
        war_id        = self._socket_handler._war_id
        team_id       = self._socket_handler._team_id
        enemy_team_id = self._socket_handler._enemy_team_id
        enemy_user_id = int(packet.enemy_user_id)

        war_result_logic = WarResultLogic()

        redis_user = RedisUserData()
        #######################################################################

        # 現在のターンを取得する #### todo:: ※redisにて管理。他の対戦相手を選んだ時に初期化する
        now_turn_number = redis_user.get_now_turn_number(war_id, team_id, user_id)
        now_turn_number += 1

        #### todo:: Redisからステータス取得する
        player_status = redis_user.get_user_status(war_id, team_id, user_id)
        enemy_status = redis_user.get_user_status(war_id, enemy_team_id, packet.target_id)

        player = User(player_status)
        player.action_type = packet.act_type
        player.skill_id = packet.skill_id
        player.target_user_id = packet.target_id

        # 相手のロジック決定
        enemy = User(enemy_status)
        enemy.target_user_id = user_id

        # 相手の行動パターンを取得する ※batchにてredisに登録しておく？もしくは直接取得？
        enemy_logic_data = [] #redis_user.get_enemy_logic_data(player.target_user_id) #### todo:: 闘竜門を参考に取得する

        enemy.action_type, enemy.skill_id = self.__get_enemy_now_turn_logic(enemy_logic_data, now_turn_number)

        # スキル発動チェック
        pl_exec_skill_level = 0
        if player.is_skill_attack():

            pl_exec_skill_level = redis_user.get_enable_skill_level(war_id, team_id, user_id, player.skill_id)
            if pl_exec_skill_level <= 0:
                player.action_type = ActionType.normal_attack
        player.skill_level = pl_exec_skill_level

        # このターンでのアクション内容を保存(ためる用) #### todo:: ※redisにて管理
        # redis_user.regist_now_turn_action()

        # 両者のロジック及びパラメータを元に攻撃ヒット判定
        player.is_hit = player.is_hit_attack(enemy)
        enemy.is_hit = enemy.is_hit_attack(player)

        # 先攻後攻決め
        order = [player, enemy]
        if player.is_skill_attack():
            # プレイヤーを先攻
            player.is_first = 1
            enemy.is_first = 0
        else:
            random.shuffle(order)
            order[0].is_first = 1
            order[1].is_first = 0

        # ダメージ計算(この時点で気絶はまだ考慮しないので確定ではない)
        for i in range(len(order)):
            offense = order[i]
            defense = order[i - 1]

            if not offense.is_hit:
                offense.do_damage = 0
                continue

            if offense.is_normal_attack():

                if offense.is_critical(defense, BATTLE_LOGIC_BASE_CRITICAL_RATE_ATK):
                    offense.is_critical_atk = True

                if defense.is_critical(offense, BATTLE_LOGIC_BASE_CRITICAL_RATE_DEF):
                    offense.is_critical_def = True

                offense.do_damage = defense.calc_damage(offense)
            elif offense.is_skill_attack():

                offense.do_damage = defense.calc_skill_damage(offense.skill_id, offense.skill_level, offense)

        player.do_damage = 10000
        enemy.do_damage = 1

        # データ更新処理 #### todo::
        initiative_side = 0 if player.is_first == 1 else 1
        updated_data = redis_user.update_user_data(war_id,
                                                    now_turn_number,
                                                    initiative_side,
                                                    team_id,
                                                    user_id,
                                                    player.action_type,
                                                    player.skill_id,
                                                    player.is_hit,
                                                    player.do_damage,
                                                    enemy_team_id,
                                                    enemy_user_id,
                                                    enemy.action_type,
                                                    enemy.skill_id,
                                                    enemy.is_hit,
                                                    enemy.do_damage)

        if updated_data['type'] != 'ok':
            self._socket_handler.send_message_to_myself({'status':updated_data['status']})
            return

        player.result_value = updated_data['player_do_damage']
        player.is_dead = True if updated_data['player_is_dead'] == '1' else False
        enemy.result_value = updated_data['enemy_do_damage']
        enemy.is_dead = True if updated_data['enemy_is_dead'] == '1' else False

        player_skill_gauge = updated_data['player_skill_gauge']
        player_skill_data = [
            {'skill_id':1, 'percent': int(player_skill_gauge[0])},
            {'skill_id':2, 'percent': int(player_skill_gauge[1])},
            {'skill_id':3, 'percent': int(player_skill_gauge[2])},
        ]

        # 返却データ作成
        action_result_data = {
            'status': 'ok',
            'initiative_side':      initiative_side,
            's_result': {
                'team_id':          self._socket_handler._team_id,
                'user_id':          self._socket_handler._user_id,
                'action_type':      int(player.action_type),
                'result_value':     int(float(player.result_value)),
                'rest_hp':          int(float(updated_data['player_rest_hp'])),
                'target_user_id':   player.target_user_id,
                'skill_id':         player.skill_id,
                'skill_lv':         pl_exec_skill_level,
                'is_hit':           bool(player.is_hit),
                'is_critical_atk':  bool(player.is_critical_atk),
                'is_critical_def':  bool(player.is_critical_def),
                'is_dead':          bool(player.is_dead),
                'skill_data':       player_skill_data,
            },
            'e_result': {
                'team_id':          self._socket_handler._enemy_team_id,
                'user_id':          packet.enemy_user_id,
                'action_type':      int(enemy.action_type),
                'result_value':     int(float(enemy.result_value)),
                'rest_hp':          int(float(updated_data['enemy_rest_hp'])),
                'target_user_id':   enemy.target_user_id,
                'skill_id':         enemy.skill_id,
                'skill_lv':         1,
                'is_hit':           bool(enemy.is_hit),
                'is_critical_atk':  bool(enemy.is_critical_atk),
                'is_critical_def':  bool(enemy.is_critical_def),
                'is_dead':          bool(enemy.is_dead),
                'skill_data': [], # クライアントでは参照しないが、構造体定義用無駄パラメーターを付与
            },
        }

        # 返却データ送信
        self._socket_handler.send_message({
            'war_id': war_id,
            'team_id': team_id,
            'action': action_result_data,
        })

        self._socket_handler.send_message({
            'war_id': war_id,
            'team_id': enemy_team_id,
            'action': action_result_data,
        })

        # 全員死亡の場合、カウントダウン開始の通知を行う
        if updated_data['is_notify_countdown'] == True:

            death_team_id = team_id
            if updated_data['emteam_is_dead_all'] == True:
                death_team_id = enemy_team_id

            self._socket_handler.send_message({
                'war_id': war_id,
                'team_id': team_id,
                'result': {
                    'death_team_id': death_team_id,
                    'rest_seconds': END_COUNTDOWN_TIME,
                },
            })
            self._socket_handler.send_message({
                'war_id': war_id,
                'team_id': enemy_team_id,
                'result': {
                    'death_team_id': death_team_id,
                    'rest_seconds': END_COUNTDOWN_TIME,
                },
            })

        return True

    # 相手のロジック決定
    def __get_enemy_now_turn_logic(self, enemy_logic_data, now_turn_number):
        
        if not enemy_logic_data:
            return ActionType.normal_attack, 0

        enemy_logics = json.loads(enemy_logic_data)
        current_logic = [row for row in enemy_logics if row['battle_turn'] == now_turn_number]
        if not current_logic:
            return ActionType.normal_attack, 0

        battle_logic_id = current_logic[0]['battle_logic_id']

        # 闘竜門でのスキルを抗争用のIDに変換する
        if battle_logic_id == 3:
            return ActionType.skill_attack, current_logic[0]['param1']

        return ActionType.normal_attack, 0


class User(object):

    def __init__(self, status_data):

        self.action_type        = -1
        self.result_value       = 0
        self.target_user_id     = 0
        self.skill_id           = 0
        self.is_hit             = True
        self.is_critical_atk    = False
        self.is_critical_def    = False
        self.is_dead            = False
        self.is_first           = False
        self.do_damage          = 0 # 途中計算用
        self.is_before_charged  = False
        self.skill_id           = 0
        self.skill_level        = 0

        self.atk            = status_data['atk']
        self.deffence       = status_data['def']
        self.agi            = status_data['agi']
        self.player_co_atk  = status_data['player_atk']
        self.player_co_def  = status_data['player_def']
        self.player_co_agi  = status_data['player_agi']
        self.enemy_co_atk   = status_data['enemy_atk']
        self.enemy_co_def   = status_data['enemy_def']
        self.enemy_co_agi   = status_data['enemy_agi']
        self.base_atk       = status_data['base_atk']
        self.base_def       = status_data['base_def']
        self.base_agi       = status_data['base_agi']

    def is_hit_attack(self, other_user):

        # スキル攻撃であれば必ずHIT
        if self.is_skill_attack():
            return True

        min_rate    = BATTLE_LOGIC_HIT_RATE_MIN
        max_rate    = BATTLE_LOGIC_HIT_RATE_MAX
        default     = BATTLE_LOGIC_HIT_RATE_DEFAULT
        const       = BATTLE_LOGIC_HIT_RATE_CONST

        agi = max(1, self.agi * self.player_co_agi * other_user.enemy_co_agi)
        target_agi = max(1, other_user.agi * other_user.player_co_agi * self.enemy_co_agi)

        share = agi / float(agi + target_agi)
        rate = default + (share - const)
        rate = min(max(rate, min_rate), max_rate)

        return random.randint(0, 100) < math.floor(100 * rate)

    # 通常攻撃か？
    def is_normal_attack(self):

        if self.action_type == ActionType.normal_attack:
            return True
        return False

    # スキル攻撃か？
    def is_skill_attack(self):

        if self.action_type == ActionType.skill_attack:
            return True
        return False

    # クリティカルHITか？
    def is_critical(self, other_user, base_critical_rate):

        threshold = BATTLE_LOGIC_CRITICAL_RATE_THRESHOLD
        critical_rate = self.agi / max(1, self.agi + other_user.agi)
        critical_rate = min(1.0, max(0, critical_rate - threshold) + base_critical_rate)

        return random.random() <= critical_rate

    # 通常ダメージ値を算出
    def calc_damage(self, other_user, **kwargs):

        critical_atk = self.__get_critical_atk(other_user.is_critical_atk)
        critical_def = self.__get_critical_def(other_user.is_critical_def)

        other_atk = max(1, other_user.atk * other_user.player_co_atk * self.enemy_co_atk )
        self_def = max(1, self.deffence * self.player_co_def * other_user.enemy_co_def)
        value = (other_atk * critical_atk - self_def * critical_def)
        value = max(1, value)

        return int(math.floor(min(value, BATTLE_LOGIC_MAX_DAMAGE)))

    # スキルによるダメージ値を算出
    def calc_skill_damage(self, skill_id, skill_level, other_user, **kwargs):

        other_atk = max(1, other_user.atk * other_user.player_co_atk * self.enemy_co_atk )
        self_def = max(1, self.deffence * self.player_co_def * other_user.enemy_co_def)

        if skill_id == 1:
            skill_table = [1, 2, 3, 4, 5]
            other_atk = other_atk + other_user.base_atk * skill_table[int(skill_level) - 1] + 10
        elif skill_id == 2:
            skill_table = [1, 2, 3, 4, 5]
            other_atk = other_atk + other_user.base_def * skill_table[int(skill_level) - 1] + 10
        elif skill_id == 3:
            skill_table = [2, 4, 6, 8, 10]
            other_atk = other_atk + other_user.base_agi * skill_table[int(skill_level) - 1] + 10

        value = other_atk - self_def
        value = max(1, value)

        return int(math.floor(min(value, BATTLE_LOGIC_MAX_DAMAGE)))


    def __get_critical_atk(self, is_critical):
        u"""
        クリティカル時の係数(攻撃)を取得する.
        """
        if not is_critical:
            return 1.0

        upper = BATTLE_LOGIC_CRITICAL_COEF_ATK_UPPER
        lower = BATTLE_LOGIC_CRITICAL_COEF_ATK_LOWER

        return lower + (upper - lower) * random.random()

    def __get_critical_def(self, is_critical):
        u"""
        クリティカル時の係数(防御)を取得する.
        """
        if not is_critical:
            return 1.0

        return 0.0

    def __get_damage_fluctuation(self):
        u"""
        ダメージのゆらぎを取得する.
        """
        upper = BATTLE_LOGIC_DAMAGE_FLUCTUATION_RANGE_UPPER
        lower = BATTLE_LOGIC_DAMAGE_FLUCTUATION_RANGE_LOWER

        return lower + (upper - lower) * random.random()

