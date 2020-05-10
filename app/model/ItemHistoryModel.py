#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from Utility import get_now_datetime, get_serial_date
from Define import ConsumptionItem

class ItemHistoryModel(BaseModel):

    def __init__(self, db):

        super(ItemHistoryModel, self).__init__(db)

    # ログデータ追加
    def add_data(self, user_id, item_mst_id, quantity):

        enum_str = ""
        if item_mst_id == int(ConsumptionItem.small) or item_mst_id == int(ConsumptionItem.small_private):
            enum_str = "heal_small"
        elif item_mst_id == int(ConsumptionItem.big) or item_mst_id == int(ConsumptionItem.big_private):
            enum_str = "heal_big"
        elif item_mst_id == int(ConsumptionItem.aed) or item_mst_id == int(ConsumptionItem.aed_private):
            enum_str = "aed"

        self._db.execute("insert into item_history (user_id, category, item_type, quantity, created) values (%s, %s, %s, %s, now())", (user_id, 'war', enum_str, int(quantity)))

    def add_datas(self, data):

        d = []
        for i in range(0, len(data)):
            d.append((data[i]["user_id"],
                      int(data[i]["category"]) + 1,
                      int(data[i]["item_type"]) + 1,
                      data[i]["quantity"]))
        sql = 'INSERT INTO item_history (user_id, category, item_type, quantity, created) ' \
              'VALUES (%s, %s, %s, %s, NOW())'
        self._db.executemany(sql, d)
