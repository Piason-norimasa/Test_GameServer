#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from Utility import get_now_datetime
from datetime import timedelta, datetime

class TeamDataModel(BaseModel):

    def __init__(self, db):

        super(TeamDataModel, self).__init__(db)

    def get_team_data_by_id(self, team_id):

        sql = 'select * from team where id = %s'
        self._db.execute(sql, (team_id, ))

        return self._db.fetchone()

    def get_team_data(self, win_team_id, lose_team_id):

        sql = 'select * from team where id in (%s, %s)'
        self._db.execute(sql, (win_team_id, lose_team_id))

        return self._db.fetchall()

    # 傘下チームを取得
    def get_child_team(self, parent_team_id):

        sql = 'select id from team where parent_team_id = %s and delete_flg = 0'
        self._db.execute(sql, (parent_team_id,))
        
        return self._db.fetchall()

    # チームステータスを更新
    def update_team_status(self, team_id, win_count, war_class_id):

        now_datetime = get_now_datetime()

        sql = 'update team set win = %s, win_straight_count = win_straight_count + 1, war_class_id = %s, updated = %s where id = %s'
        self._db.execute(sql, (win_count, war_class_id, now_datetime, team_id))

    # 抗争敗北としてチームを更新
    def update_team_as_war_lose(self, team_id, war_class_id):

        now_datetime = get_now_datetime()

        # 傘下には入らず敗北数更新
        sql = 'update team set lose = lose + 1, win_straight_count = 0, child_team_id = null, war_class_id = %s, updated = %s where id = %s'
        self._db.execute(sql, (war_class_id, now_datetime, team_id))

    # 傘下チームの登録を削除する
    def update_unregist_child_team(self, team_id):

        now_datetime = get_now_datetime()

        # 敗北チームに傘下がいた場合は解放
        sql = 'update team set parent_team_id = null, updated = %s where parent_team_id = %s'
        self._db.execute(sql, (now_datetime, team_id))

    # そのチームに所属しているユーザーのIDを取得
    def get_user_id_list_by_team_id(self, team_id):

        sql = 'select id from user where team_id = %s and delete_flg = 0'
        self._db.execute(sql, (team_id,))

        return self._db.fetchall()

    # チームの合計ランキングポイントを取得
    def get_team_sum_ranking_point(self, team_id, target_datetime):

        sql = 'select sum(point) as total_point from team_ranking_point_record where team_id = %s and created > %s'
        self._db.execute(sql, (team_id, target_datetime.strftime('%Y-%m-%d %H:%M:%S')))
        
        return self._db.fetchone()['total_point']

    # ランキングポイントをレコードに追加
    def insert_team_ranking_point(self, event_id, type, win_team_id, lose_team_id, ranking_point):

        now_datetime = get_now_datetime()

        sql = 'insert into team_ranking_point_record (event_id, type, team_id, point, created) values (%s, %s, %s, %s, %s)'
        values = []
        values.append((event_id, type, win_team_id, ranking_point, now_datetime))
        values.append((event_id, type, lose_team_id, -ranking_point, now_datetime))

        self._db.executemany(sql, values)

