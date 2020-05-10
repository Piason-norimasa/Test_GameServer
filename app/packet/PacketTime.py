#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import tornado.options
from tornado.options import options

from PacketBase import Packet, PacketHandler

from Utility import get_serial_date
from RedisWarData import RedisWarData
from Define import END_COUNTDOWN_TIME

import math, random
from WarResultLogic import WarResultLogic

class PacketTimeHandler(PacketHandler):
    

    def __init__(self, socket_handler, data):

        super(PacketTimeHandler, self).__init__(socket_handler, data)

    def _execute(self):

        war_id          = self._socket_handler._war_id
        team_id         = self._socket_handler._team_id
        enemy_team_id   = self._socket_handler._enemy_team_id
        user_id         = self._socket_handler._user_id

        # 抗争終了時間を過ぎているかチェック
        now_time = get_serial_date()
        if now_time < self._socket_handler._war_end_time:

            self.__check_war_end_countdown(war_id, team_id)
            return True

        war_result_logic = WarResultLogic()

        # timeup
        redis_war = RedisWarData()
        result = redis_war.timeup_judge_win_team(war_id, team_id, enemy_team_id, options.redis_war_data_expire, random.choice(('0', '1')))

        win_team_id     = result['win']
        lose_team_id    = result['lose']
        enemy_count     = result['enemy_count']
        finish_attack   = result['finish_attack']

        # タイムアップによる抗争勝敗を通知する
        self.__send_win_or_lose_to_team(war_id, win_team_id, lose_team_id, finish_attack)

        if result['type'] == 'timeup':

            # 抗争終了時の参戦メンバーを取得
            members = redis_war.get_end_member(war_id, win_team_id, lose_team_id)

            # 抗争結果登録
            war_result_logic.regist_war_result(war_id, win_team_id, lose_team_id, enemy_count, members['win'], members['lose'], is_timeup = 1)

            # 抗争終了通知
            self.__send_finish_to_team(war_id, win_team_id, lose_team_id)

        return True

    # 抗争終了時間チェック
    def __check_war_end_countdown(self, war_id, team_id):

        redis_war = RedisWarData()
        result = redis_war.war_get_end_countdown(war_id)

        if result['type'] != 'ok':
            return

        # 抗争終了カウントダウンチェック
        countdown_data = result['data']
        if countdown_data[0] == '1':

            start_time = int(countdown_data[1])
            remain_time = END_COUNTDOWN_TIME - (get_serial_date() - start_time)
            if remain_time < 0:
                remain_time = 0

            # 抗争終了処理を実行
            lose_team_id = countdown_data[3]            
            self._socket_handler.send_message_to_myself({
                'war_id': war_id,
                'team_id': team_id,
                'result': {
                    'death_team_id': lose_team_id,
                    'rest_seconds': remain_time,
                },
            })

    # 抗争勝敗を通知する
    def __send_win_or_lose_to_team(self, war_id, win_team_id, lose_team_id, finish_attack_user):

        send_data = {
            'war_id': war_id,
            'team_id': win_team_id,
            'result': { 'type': 'timeup', 'result': 'win', 'user': finish_attack_user },
        }
        self._socket_handler.send_message(send_data)

        send_data = {
            'war_id': war_id,
            'team_id': lose_team_id,
            'result': { 'type': 'timeup', 'result': 'lose' },
        }
        self._socket_handler.send_message(send_data)

    # 抗争終了を通知する
    def __send_finish_to_team(self, war_id, win_team_id, lose_team_id):

        self._socket_handler.send_message({
            'war_id': war_id,
            'team_id': win_team_id,
            'finish': 'ok',
        })
        self._socket_handler.send_message({
            'war_id': war_id,
            'team_id': lose_team_id,
            'finish': 'ok',
        })        
