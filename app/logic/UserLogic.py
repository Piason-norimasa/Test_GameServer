#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from datetime import timedelta, datetime
from MissionModel import MissionModel

from Utility import get_serial_date, get_now_datetime

class UserLogic(object):

    # ミッション情報を更新
    def update_mission_status(self, user_id, cur, amount, **kwargs):

        mission_model = MissionModel(cur)
        
        condition_type = None
        if 'condition_type' in kwargs:
            condition_type = kwargs['condition_type']
        else:
            return
        
        method = None
        if 'method' in kwargs:
            method = kwargs['method']
        else:
            method = 'count_up'
        
        if method == 'count_up':
            mission_model.count_up_value(user_id, condition_type, amount)
        elif method == 'set':
            mission_model.set_value(user_id, condition_type, amount)
        elif method == 'set_gt':
            mission_model.set_value(user_id, condition_type, amount, '>')

    # ユーザータイトルを更新
    def update_user_title(self, user_id, cur, updated_data):
        pass
