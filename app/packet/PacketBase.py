#!/usr/bin/env python
# -*- coding: utf-8 -*-i

import logging

import hmac
import hashlib
from RedisWarData import RedisWarData
from Utility import get_serial_date
from Define import END_COUNTDOWN_TIME

from WarResultLogic import WarResultLogic

# リクエストパケット(基底クラス)
class Packet(object):

    _hash_code  = None
    _hash_src   = ''

    def __init__(self):
        pass

    # ハッシュチェック
    def is_validate_hash(self):

        if self._hash_code == self._create_data_hash():
            return True

        return False

    # 継承先クラスでオーバーライド
    def _create_data_hash(self):

        return 'test'

    # TODO: ReflectionでHash算出できたらいいな
    # classメンバー変数のHash値を算出
    def _create_data_hash(self, str):

        return hmac.new('Napha4thaifup3he', str, hashlib.sha256).hexdigest()

# パケット処理(基底クラス)
class PacketHandler(object):

    _socket_handler     = None
    _packet             = None
    _data               = None
    _type               = ''

    def __init__(self, socket_handler, data):

        self._socket_handler   = socket_handler
        self._data             = data

    def _pre_execute(self):

        redis_war = RedisWarData()
        result = redis_war.war_get_end_countdown(self._socket_handler._war_id)

        if result['type'] != 'ok' or not hasattr(self._socket_handler, '_war_id'):
            return True

        # 抗争終了カウントダウンチェック
        countdown_data = result['data']
        if countdown_data[0] == '1':

            start_time = int(countdown_data[1])
            remain_time = END_COUNTDOWN_TIME - (get_serial_date() - start_time)
            if remain_time <= 0:

                # カウントダウン処理終了
                redis_war.war_end_countdown(self._socket_handler._war_id)

                # 抗争終了処理を実行
                war_result_logic    = WarResultLogic()
                win_team_id         = countdown_data[2]
                lose_team_id        = countdown_data[3]
                war_id              = self._socket_handler._war_id

                # 抗争終了時の参戦メンバーを取得
                members = redis_war.get_end_member(war_id, win_team_id, lose_team_id)

                # 抗争結果登録
                war_result_logic.regist_war_result(war_id, win_team_id, lose_team_id, 0, members['win'], members['lose'], is_timeup = 0)

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
                return False

        return True

    def _execute(self):
        return True

    def _post_execute(self):
        return True

    # パケット処理関数
    def execute(self):

        is_result = self._pre_execute()
        if is_result == False:
            return True

        is_result = self._execute()
        if is_result == False:
            return False

        is_result = self._post_execute()

        return is_result
