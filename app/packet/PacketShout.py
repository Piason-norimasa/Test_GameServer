#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import define, options

from PacketBase import Packet, PacketHandler
from RedisWarData import RedisWarData

class PacketShoutHandler(PacketHandler):

    def __init__(self, socket_handler, data):

        super(PacketShoutHandler, self).__init__(socket_handler, data)

    def _execute(self):

        user_id         = int(self._socket_handler._user_id)
        user_name       = str(self._socket_handler._user_name)
        war_id          = self._socket_handler._war_id
        team_id         = self._socket_handler._team_id
        enemy_team_id   = self._socket_handler._enemy_team_id

        self._socket_handler.send_message({
            'war_id': war_id,
            'team_id': team_id,
            'shout': { 'user_id': user_id, 'user_name': user_name, 'data': self._data },
        })

        self._socket_handler.send_message({
            'war_id': war_id,
            'team_id': enemy_team_id,
            'shout': { 'user_id': user_id, 'user_name': user_name, 'data': self._data },
        })

        return True
