#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from Utility import get_now_datetime, get_serial_date

class CampaignModel(BaseModel):

    def __init__(self, db):

        super(CampaignModel, self).__init__(db)

    # 抗争用の場数アップキャンペーン情報を取得
    def get_war_exp_campaign_data(self):

        now_datetime = get_now_datetime()

        sql = 'select id from campaign where name = %s and open_datetime <= %s and end_datetime >= %s'
        self._db.execute(sql, ('war_exp_up', now_datetime, now_datetime))

        return self._db.fetchone()

    # 経験値アップキャンペーン情報を取得
    def get_exp_campaign_data(self):

        now_datetime = get_now_datetime()

        # キャンペーン取得
        campaign_names = [ 'exp_up' ]
        sql = '''
            SELECT id, name, setting_value, open_datetime, end_datetime FROM campaign
            WHERE
                name in (%s) AND
                open_datetime <= %s AND
                end_datetime > %s AND
                is_valid = 1
        ''' % (','.join(['%s' for row in campaign_names]), '%s', '%s')

        self._db.execute(sql, campaign_names + [now_datetime, now_datetime])

        return  self._db.fetchall()

    # 経験値アップキャンペーン情報を取得
    def get_beginner_exp_campaign_data(self):

        now_datetime = get_now_datetime()

        # キャンペーン取得
        campaign_names = [ 'beginer_exp_up_%' ]
        sql = '''
            SELECT id, name, setting_value, open_datetime, end_datetime FROM campaign
            WHERE
                name like %s AND
                open_datetime <= %s AND
                end_datetime > %s AND
                is_valid = 1
        '''

        self._db.execute(sql, (campaign_names, now_datetime, now_datetime))

        return self._db.fetchall()
