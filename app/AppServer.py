#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import ssl
import threading
import tornado
from tornado import websocket, web, ioloop, httpclient, httpserver
import tornado.options
from tornado.options import define, options

from redis import Redis, ConnectionPool
import MySQLdb
import datetime

from AppHandler import IndexHandler, SocketHandler
from AppMonitor import fixed_update

# アプリケーションサーバー本体
class AppServer(tornado.web.Application):

    MONITORING_INTERVAL_TIME = 10000

    __is_initialize = False
    __socket_pool   = None
    __app_pool      = None
    __ws_client     = {}

    # シングルトンパターン化
    def __new__(class_obj, *args, **kwargs):

        if not hasattr(class_obj, "__instance__"):

            class_obj.__instance__ = super(AppServer, class_obj).__new__(class_obj, *args, **kwargs)

        return class_obj.__instance__

    def __init__(self):

        # TODO: このやり方はあってるのだろうか？
        if self.__is_initialize:
            return

        handlers = [
            (r'/',          IndexHandler),
            (r'/ws',        SocketHandler),
        ]
        settings = dict(
            debug=True,
        )

        tornado.web.Application.__init__(self, handlers, **settings)
        http_server = tornado.httpserver.HTTPServer(self, ssl_options = self.create_ssl_context(options.ssl_crtfile, options.ssl_keyfile))
        http_server.listen(options.web_port)
        self.listen(options.ws_port)

        # redis プール作成
        self.__socket_pool = ConnectionPool(host=options.redis_socket_host, port=options.redis_socket_port, db=options.redis_socket_db)
        self.__app_pool = ConnectionPool(host=options.redis_app_host, port=options.redis_app_port, db=options.redis_app_db)

        self.__is_initialize = True

    # SSL証明context
    def create_ssl_context(self, certfile, keyfile):

        ssl_options = {
            'certfile': certfile,
            'keyfile': keyfile,
            #"cert_reqs": self.cert_reqs,
            #'ca_certs': '/etc/ssl/bakuden_ca.crt',
            'ssl_version': ssl.PROTOCOL_TLSv1,
        }

        return ssl_options

    # サーバースタート
    def start_server(self):

        tornado.ioloop.PeriodicCallback(fixed_update, self.MONITORING_INTERVAL_TIME).start()
        tornado.ioloop.IOLoop.instance().start()

    # ソケットプール取得
    def get_socket_pool(self):
        return self.__socket_pool

    # Appプール取得
    def get_app_pool(self):
        return self.__app_pool

    # ws client取得　get_ws_client
    def get_ws_client(self, id):

        if id not in self.__ws_client:
            return []

        return self.__ws_client[id]

    def get_ws_all_client(self):
        return self.__ws_client

    # client登録
    def regist_ws_client(self, id, socket_handler):

        if id not in self.__ws_client:
            self.__ws_client[id] = []

        if socket_handler in self.__ws_client[id]:
            self.__ws_client[id].remove(socket_handler)

        for client in self.__ws_client[id]:
            if client._user_id == socket_handler._user_id and client._war_id == socket_handler._war_id:
                self.__ws_client[id].remove(client)

        # 新規登録
        self.__ws_client[id].append(socket_handler)
        logging.info('[Socket regist client] user_id:' + str(socket_handler._user_id))

    # client登録削除
    def unregist_ws_client(self, id, socket_handler):

        if id in self.__ws_client and socket_handler in self.__ws_client[id]:
            self.__ws_client[id].remove(socket_handler)

    # websocket connection数出力
    def logging_websocket_client_count(self):

        count = 0
        for id, data in self.__ws_client.items():
            count += len(data)
        logging.info('[Socket client count]: ' + str(count))


    # TODO: このメソッドをどこに定義するのが良いのか ？？？
    # db connection 取得
    def get_db_connection(self, db_type):

        host    = options.db_master_host
        port    = options.db_master_port
        db_user = options.db_user
        db_pass = options.db_pass
        db_name = options.db_name

        if db_type == 'master':
            pass

        elif db_type == 'slave':

            host = options.db_slave_host
            port = options.db_slave_port
        elif db_type == 'log':

            host = options.db_log_host
            port = options.db_log_port
            db_name = options.db_log_name
        else:
            return None

        self._db = MySQLdb.connect(charset='utf8', 
                                    init_command='SET NAMES UTF8',
                                    host=host, 
                                    port=port,
                                    db=db_name, 
                                    user=db_user, 
                                    passwd=db_pass)
        self._db.cursorclass = MySQLdb.cursors.DictCursor

        return self._db
        
