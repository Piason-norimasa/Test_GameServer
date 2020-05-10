#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import options

from PacketBase import Packet, PacketHandler
from RedisWarData import RedisWarData

from Utility import get_serial_date

class PacketSelect(Packet):

    _hash_src       = 'wsm'

    user_id         = None
    user_name       = None
    enemy_user_id   = None

    def __init__(self, data):

        self.user_id        = str(data['user_id'])
        self.user_name      = str(data['user_name'])
        self.enemy_user_id  = str(data['enemy_user_id'])
        self._hash_code     = str(data['code'])

    def _create_data_hash(self):

        hash_value = self._hash_src
        hash_value += str(self.user_id)
        hash_value += str(self.user_name)
        hash_value += str(self.enemy_user_id)

        return super(PacketSelect, self)._create_data_hash(hash_value)

class PacketSelectHandler(PacketHandler):
    

    def __init__(self, socket_handler, data):

        super(PacketSelectHandler, self).__init__(socket_handler, data)

    def _execute(self):

        # リクエストパラメーターチェック
        packet = PacketSelect(self._data)
        if packet.is_validate_hash() == False:
            return False

        user_id         = int(packet.user_id)
        user_name       = packet.user_name
        enemy_user_id   = int(packet.enemy_user_id)
        enemy_team_id   = self._socket_handler._enemy_team_id
        war_id          = self._socket_handler._war_id
        team_id         = self._socket_handler._team_id

        redis_war = RedisWarData()
        result = redis_war.select_enemy(war_id, team_id, user_id, user_name, enemy_user_id, get_serial_date(), options.redis_war_data_expire)

        is_ok = True
        if result['status'] == 'before_start':
            is_ok = False

        if result['status'] == 'is_dead':
            is_ok = False

        if is_ok:

            # 全員に通知
            self._socket_handler.send_message({
                'war_id': war_id,
                'team_id': team_id,
                'select': { 'status':'ok', 'team_id':team_id, 'user_id':user_id, 'user_name':user_name, 'before_enemy':result['before_enemy'], 'after_enemy':result['after_enemy'] },
            })

            self._socket_handler.send_message({
                'war_id': war_id,
                'team_id': enemy_team_id,
                'select': { 'status':'ok', 'team_id':team_id, 'user_id':user_id, 'user_name':user_name, 'before_enemy':result['before_enemy'], 'after_enemy':result['after_enemy'] },
            })
        else:

            # 敵の選択に失敗したので自分にのみ, レスポンス
            self._socket_handler.send_message_to_myself({
                'war_id': war_id,
                'team_id': team_id,
                'select': { 'status':result['status'], 'user_id': user_id, 'user_name': user_name, 'enemy_user_id': enemy_user_id },
            })

        return True
