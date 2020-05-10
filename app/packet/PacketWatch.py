#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import tornado.options
from tornado.options import options

from PacketBase import Packet, PacketHandler
from PacketTime import PacketTimeHandler
from RedisWarData import RedisWarData

from AppServer import AppServer

class PacketWatch(Packet):

    _hash_src       = 'wwm'

    war_id          = None 
    team_id         = None
    user_id         = None
    enemy_team_id   = None 

    def __init__(self, data):

        self.war_id         = str(data['war_id'])
        self.team_id        = str(data['team_id'])
        self.user_id        = str(data['user_id'])
        self.enemy_team_id  = str(data['enemy_team_id'])
        self._hash_code     = str(data['code'])

    def _create_data_hash(self):

        hash_value = self._hash_src
        hash_value += str(self.war_id)
        hash_value += str(self.team_id)
        hash_value += str(self.user_id)
        hash_value += str(self.enemy_team_id)

        return super(PacketWatch, self)._create_data_hash(hash_value)

class PacketWatchHandler(PacketHandler):

    def __init__(self, socket_handler, data):

        super(PacketWatchHandler, self).__init__(socket_handler, data)

    def _execute(self):

        # リクエストパラメーターチェック
        packet = PacketWatch(self._data)
        if packet.is_validate_hash() == False:
            return False

        app_instance    = AppServer()

        war_id          = int(packet.war_id)
        user_id         = int(packet.user_id)
        team_id         = int(packet.team_id)
        enemy_team_id   = int(packet.enemy_team_id)

        # このsocket_handlerがws_clientに登録されているかチェック
        is_reconnect = True
        ws_client_list  = app_instance.get_ws_client(war_id)
        for client in ws_client_list:
            if client._user_id == user_id and client._war_id == war_id:
                is_reconnect = False
                break

        if is_reconnect:
            redis_war_data  = RedisWarData()
            redis_war_data.exit_war(war_id, user_id, enemy_team_id, options.redis_war_data_expire)
            return False

        # 続けてPacketTimeHandlerで時間切れ確認
        packet_time_handler = PacketTimeHandler(self._socket_handler, self._data)

        return packet_time_handler.execute()
