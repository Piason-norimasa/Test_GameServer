#!/usr/bin/env python
# -*- coding: utf-8 -*-

import msgpack
import hmac
import hashlib

class WebApi(object):

    _request_handler    = None
    _data               = None

    def __init__(self, request_handler, data):

        self._request_handler = request_handler
        self._data = data

    # ハッシュ値生成
    def _get_hash_code(self, str):

        return hmac.new('Napha4thaifup3he', str, hashlib.sha256).hexdigest()

    # パラメーターチェック
    def _is_validate_parameters(self, data):

        return False

    # _execute前実行関数(継承先で必要なら実装)
    def _pre_execute(self):
        pass

    # API処理実行(継承先で実装)
    def _execute(self):
        pass

    # _execute後実行関数(継承先で必要なら実装)
    def _post_execute(self):
        pass

    # API実行
    def execute(self):

        self._pre_execute()
        self._execute()
        self._post_execute()
