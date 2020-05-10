#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from datetime import timedelta, datetime
from Utility import get_now_datetime, get_serial_date

class MissionModel(BaseModel):

    def __init__(self, db):

        super(MissionModel, self).__init__(db)

    def update_mission_status(self, mission_id, user_id, data):

        query = '''
            update  mission_user_status
            set     lv=%s, prize_received=%s, updated=%s
            where mission_id=%s and user_id=%s
        '''
        self._db.execute(query, (data['lv'], data['prize_received'], datetime.now(), mission_id, user_id))

    def count_up_value(self, user_id, condition_type, amount):

        result_set = self.__get_status_by_condition_type(user_id, condition_type)

        # 各ステータスの値を更新
        for row in result_set:

            # 初期値チェック
            row['count'] = row['count'] if row['count'] else 0
            row['lv'] = row['lv'] if row['lv'] else 0
            row['prize_received'] = row['prize_received'] if row['prize_received'] else 0
            
            if row['prize_received'] == 0:
                # カウントアップ
                row['count'] = row['count'] + amount
                
                now_datetime = get_now_datetime()
                
                # 各行を初期化、更新
                self._db.execute('''
                    insert into mission_user_status
                        (mission_id, user_id, count, lv, updated, created)
                    values
                        (%s, %s, %s, %s, %s, %s)
                    on duplicate key update
                        count=%s,
                        lv=%s,
                        updated=%s
                ''', (
                    # 初期化用
                    row['mission_id'], user_id, row['count'], row['lv'], now_datetime, now_datetime,
                    
                    # 更新用
                    row['count'], row['lv'], now_datetime
                ))
    
    def set_value(self, user_id, condition_type, amount, test_opr=None):

        result_set = self.__get_status_by_condition_type(user_id, condition_type)

        # 各ステータスの値を更新
        for row in result_set:
            # 初期値チェック
            row['count'] = row['count'] if row['count'] else 0
            row['lv'] = row['lv'] if row['lv'] else 0
            row['prize_received'] = row['prize_received'] if row['prize_received'] else 0
            
            if row['prize_received'] == 0:

                if test_opr is None or eval('%s %s %s' % (amount,test_opr,row['count'])):
                    # カウントアップ
                    row['count'] = amount
                    
                    now_datetime = get_now_datetime()
                    
                    # 各行を初期化、更新
                    self._db.execute('''
                        insert into mission_user_status
                            (mission_id, user_id, count, lv, updated, created)
                        values
                            (%s, %s, %s, %s, %s, %s)
                        on duplicate key update
                            count=%s,
                            lv=%s,
                            updated=%s
                    ''', (
                        # 初期化用
                        row['mission_id'], user_id, row['count'], row['lv'], now_datetime, now_datetime,
                        
                        # 更新用
                        row['count'], row['lv'], now_datetime
                    ))
    
    # conditionタイプによるミッション情報を取得
    def __get_status_by_condition_type(self, user_id, condition_type):

        query = '''
            select  mission.id as mission_id,
                    mission.accomplishment_limit,
                    mission.condition_type,
                    mission.condition_value,
                    mission.condition_severity,
                    mission.parent_mission_id,
                    mission.navigation_id,
                    status.user_id,
                    status.count,
                    status.lv,
                    status.prize_received
            from mission
            left join mission_user_status as status on status.user_id = %s and status.mission_id = mission.id
            where   mission.condition_type = %s and
                    now() between mission.begin_datetime and mission.end_datetime
        '''
        self._db.execute(query, (user_id, condition_type))

        return self._db.fetchall()

