#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import tornado.options
from tornado.options import options

from AppServer import AppServer
from PacketBase import Packet, PacketHandler
from RedisWarData import RedisWarData
from Utility import get_serial_date
from Define import END_COUNTDOWN_TIME

class PacketRegist(Packet):

    _hash_src   = 'wsr'

    war_id      = None
    team_id     = None
    user_id     = None
    user_name   = None

    def __init__(self, data):

        self.war_id = str(data['war_id'])
        self.team_id = str(data['team_id'])
        self.user_id = str(data['user_id'])
        self.user_name = str(data['user_name'])
        self._hash_code = str(data['code'])

    def _create_data_hash(self):

        hash_value = self._hash_src
        hash_value += str(self.war_id)
        hash_value += str(self.team_id)
        hash_value += str(self.user_id)
        hash_value += str(self.user_name)

        return super(PacketRegist, self)._create_data_hash(hash_value)

class PacketRegistHandler(PacketHandler):


    def __init__(self, socket_handler, data):

        super(PacketRegistHandler, self).__init__(socket_handler, data)

    # Regist処理時の場合は事前チェック処理をしない
    def _pre_execute(self):
        pass

    def _execute(self):

        # リクエストパラメーターチェック
        packet = PacketRegist(self._data)
        if packet.is_validate_hash() == False:
            return False

        redis_war = RedisWarData()
        result = redis_war.enter_war(packet.war_id,
                                    packet.team_id,
                                    packet.user_id,
                                    get_serial_date(),
                                    options.redis_war_data_expire)

        if result['type'] == 'error':

            self._socket_handler.send_message_to_myself({'regist': 'NG', 'status': result['status']})
            return True

        enemy_team_id   = int(result['enemy_team_id'])
        war_start_time  = int(result['start_time'])
        war_end_time    = int(result['end_time'])

        self.__regist_ws_client(packet, enemy_team_id, war_start_time, war_end_time)
        self._socket_handler.send_message_to_myself({'regist': 'OK', 'enemy_team_id':enemy_team_id})

        # 抗争終了カウントダウンチェック
        countdown_data = result['countdown_data']
        if countdown_data[0] == '1':

            start_time = int(countdown_data[1])
            remain_time = END_COUNTDOWN_TIME - (get_serial_date() - start_time)
            if remain_time < 0:
                remain_time = 0

            self._socket_handler.send_message_to_myself({'result': {'death_team_id':countdown_data[3], 'rest_seconds':remain_time }})

        return True

    def __regist_ws_client(self, data, enemy_team_id, war_start_time, war_end_time):

        app_instance = AppServer()

        # SocketHandler にユーザー情報を追加してAppServerに登録
        self._socket_handler._user_id		= int(data.user_id)
        self._socket_handler._user_name 	= data.user_name
        self._socket_handler._team_id       = int(data.team_id)
        self._socket_handler._enemy_team_id	= int(enemy_team_id)
        self._socket_handler._war_id		= int(data.war_id)
        self._socket_handler._war_start_time= int(war_start_time)
        self._socket_handler._war_end_time 	= int(war_end_time)

        app_instance.regist_ws_client(int(data.war_id), self._socket_handler)
