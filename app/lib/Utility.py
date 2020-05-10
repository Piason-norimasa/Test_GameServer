#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import timedelta, datetime
import re

# 現在時間取得
def get_now_datetime():

    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

# 現在時間(timestamp)取得
def get_serial_date(seconds = 0):

    delta = datetime.now() - datetime.strptime('1970-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
    return int(delta.total_seconds()) + seconds

# アイテム情報を連想配列化
def convert_item_to_dict(csv):

    ary = csv.split(',')

    item = {}
    item['category'] = int(ary[0])
    item['item_id'] = int(ary[1])
    item['count'] = int(ary[2])

    return item

# 文字列変換用クラス
class StringUtils:

    @staticmethod
    def to_camel(value, is_capitalize):

        if value is None:
            return ""

        ret = value.lower()

        words = re.split("[\s_]", ret)
        words = map(lambda x: x.capitalize(), words)
        if is_capitalize == False:
            words[0] = words[0].lower()

        return "" . join(words)
