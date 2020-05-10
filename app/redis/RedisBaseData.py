#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import os
import msgpack
from redis import Redis, ConnectionPool
import AppServer

class RedisBaseData(object):

    _redis  = None

    def __init__(self, connection_pool):

        if connection_pool is None:

            app_instance = AppServer.AppServer()
            connection_pool = app_instance.get_socket_pool()

        self._redis = Redis(connection_pool= connection_pool)

    # Luaスクリプトをロード
    def _load_lua_script(self, lua_file, sha):

        if not self._redis.script_exists(sha)[0]:

            location = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))) + '/lua'
            with open(os.path.join(location, lua_file), 'r') as f:

                lua_script = f.read()
                sha = self._redis.script_load(lua_script)

        return sha

    # Luaレスポンス
    def _lua_response(self, sha, key_num, *args):
        
        logging.info(args)
        response = msgpack.unpackb(self._redis.evalsha(sha, key_num, args))
        
        logging.info("Lua response:")
        logging.info(response)

        return response
