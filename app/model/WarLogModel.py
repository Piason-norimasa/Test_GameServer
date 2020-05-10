#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from datetime import timedelta, datetime

from Utility import get_now_datetime
import math, random

class WarLogModel(BaseModel):

    def __init__(self, db):

        super(WarLogModel, self).__init__(db)

    # 入れ替え戦結果ログを追加
    def insert_war_shuffle_result_log(self,
                                        war_league_schedule_mst_id,
                                        war_result_id,
                                        win_team_id, 
                                        win_team_prev_war_class_mst_id, 
                                        win_team_post_war_class_mst_id,
                                        lose_team_id, 
                                        lose_team_prev_war_class_mst_id, 
                                        lose_team_post_war_class_mst_id):

        sql = 'insert into war_shuffle_result_log (war_league_schedule_mst_id, war_result_id, win_team_id, win_team_prev_war_class_mst_id, win_team_post_war_class_mst_id, lose_team_id, lose_team_prev_war_class_mst_id, lose_team_post_war_class_mst_id, created)'
        sql += ' values(%s, %s, %s, %s, %s, %s, %s, %s, %s)'

        now_datetime = get_now_datetime()
        params = (war_league_schedule_mst_id, war_result_id, win_team_id, win_team_prev_war_class_mst_id, win_team_post_war_class_mst_id, lose_team_id, lose_team_prev_war_class_mst_id, lose_team_post_war_class_mst_id, now_datetime)
        self._db.execute(sql, params)
    
    # 抗争入れ替え戦結果ログを取得
    def get_war_shuffle_result_log(self, war_league_schedule_mst_id):

        sql = 'select * from war_shuffle_result_log where war_league_schedule_mst_id = %s'
        self._db.execute(sql, (war_league_schedule_mst_id, ))

        return self._db.fetchall()

    # 抗争の連続勝利数をログに保存
    def insert_war_victory_log(self, war_id, team_id, victory_count):

        now_datetime = get_now_datetime()
        now = datetime.now()

        sql = 'insert into war_victory_log (war_result_id, team_id, year, month, day, hour, victory, created) values (%s, %s, %s, %s, %s, %s, %s, %s)'
        self._db.execute(sql, (war_id, team_id, now.year, now.month, now.day, now.hour, victory_count, now_datetime))

