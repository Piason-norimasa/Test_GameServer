#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import msgpack
import json

import tornado
from tornado import websocket, web, ioloop, httpclient
import tornado.options
from tornado.options import define, options

from RedisWarData import RedisWarData

import AppServer
from Utility import StringUtils, get_serial_date

class IndexHandler(tornado.web.RequestHandler):

    __api_type = None

    def post(self):

        try:

            data = msgpack.unpackb(self.request.files['data'][0]['body'])
            self.__api_type = data['type']
            api_class = 'WebApi' + StringUtils.to_camel(self.__api_type, True)

            # WebAPI処理クラスを生成し、処理実行
            mod = __import__(api_class, fromlist = [api_class])
            class_def = getattr(mod, api_class)
            api_instance = class_def(self, data)

            # API処理実行
            api_instance.execute()

        except Exception as e:

            import traceback
            logging.error(e.message)
            logging.error(traceback.format_exc())

            self.response({ 'res': False, 'status': 'error' })

    def response(self, send_raw_data):

        send_data = msgpack.packb(send_raw_data)
        self.write(send_data)
        logging.info('[Api:' + str(self.__api_type) + '] response:' + json.dumps(send_raw_data))


class SocketHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        pass

    def on_close(self):

        try:
            if not hasattr(self, '_war_id') or not hasattr(self, '_user_id'):
                return

            # SocketHandler登録削除
            app_instance = AppServer.AppServer()
            app_instance.unregist_ws_client(self._war_id, self)

            redis_war = RedisWarData()

            # 退出によりターゲットを解除を通知
            select_enemy = redis_war.select_enemy(self._war_id, self._team_id, self._user_id, self._user_name, 0, get_serial_date(), options.redis_war_data_expire)
            if select_enemy['status'] == 'ok':
                send_data = {
                    'war_id': self._war_id,
                    'team_id': self._team_id,
                    'select': { 'status':'ok', 'team_id':int(self._team_id), 'user_id':int(self._user_id), 'before_enemy':select_enemy['before_enemy'], 'after_enemy':select_enemy['after_enemy'] },
                }
                self.send_message(send_data)

            # 退出によるデータ更新し、チームメンバーに通知する
            redis_war.exit_war(self._war_id, self._user_id, self._team_id, options.redis_war_data_expire)

            #logging.info('[Socket close] user_id: ' + str(self._user_id))

        except Exception as e:

            import traceback
            logging.error(e.message)
            logging.error(traceback.format_exc())

    # ソケットクローズ処理
    def __close_process(self):

        # TODO: self.close を呼んでもon_closeにこないので自前で呼び出してみるが、、果たして正しいのか？
        self.close()
        self.on_close()

        logging.info('========================================[Socket close !!!] user_id: ' + str(self._user_id))

    def on_message(self, message):

        try:

            data = msgpack.unpackb(message)
            req = data['req']

            req_upper = StringUtils.to_camel(req, True)
            class_handler = 'Packet' + req_upper + 'Handler'
            class_file = 'Packet' +  req_upper

            # パケット処理クラスを生成し、処理実行
            mod = __import__(class_file, fromlist = [class_handler])
            class_def = getattr(mod, class_handler)
            obj = class_def(self, data['data'])

            ret = obj.execute()
            if ret == False:
                self.__close_process()

        except Exception as e:

            import traceback
            logging.error(e.message)
            logging.error(traceback.format_exc())

            self.__close_process()

    # 抗争参加中チームメンバー全員に送信
    def send_message(self, send_raw_data, cmd = ""):

        app_instance = AppServer.AppServer()
        war_id      = send_raw_data['war_id']
        team_id     = send_raw_data['team_id']
        
        ws_client_list = app_instance.get_ws_client(war_id)
        for client in ws_client_list:
            if int(client._team_id) == int(team_id):
                client.__send_message(client, send_raw_data, cmd)

    # 自分にのみメッセージ送信
    def send_message_to_myself(self, send_raw_data, cmd = ""):

        self.__send_message(self, send_raw_data, cmd)

    def __send_message(self, socket_handler, send_raw_data, cmd):

        send_data = msgpack.packb(send_raw_data)
        self.write_message(send_data, True)

        if hasattr(socket_handler, '_user_id'):
            #logging.info('[Socket response cmd:' + str(cmd) + ' user_id:' + str(socket_handler._user_id) + '] response:' + json.dumps(send_raw_data))
            pass
        else:
            #logging.info('[Socket response cmd:' + str(cmd) + '] response:' + json.dumps(send_raw_data))
            pass

