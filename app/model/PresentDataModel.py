#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from datetime import timedelta, datetime

class PresentDataModel(BaseModel):

    def __init__(self, db):

        super(PresentDataModel, self).__init__(db)

    # プレゼントデータをリストに追加
    def insert_present_data_list(self, present_data_list):

        if len(present_data_list) == 0:
            return

        sql = 'insert into present (user_id, category_id, item_id, message, quantity, serial, created) values (%s, %s, %s, %s, %s, %s, %s)'
        self._db.executemany(sql, present_data_list)

