#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from datetime import timedelta, datetime

from Utility import get_now_datetime
from Define import TeamActivityCategory
import math, random

class WarDataModel(BaseModel):

    def __init__(self, db):

        super(WarDataModel, self).__init__(db)

    # 勝利報酬決定
    def get_win_prize(self, league_schedule_mst_id, class_id):

        sql = 'select * from war_league_prize_win_mst where war_league_schedule_mst_id = %s and war_class_mst_id = %s'
        self._db.execute(sql, (league_schedule_mst_id, class_id))
        
        result_prize_list = self._db.fetchall()
        category_prize_list = {}
        ret_prize_list = []

        for prize_data in result_prize_list:
            if prize_data['box_category_id'] not in category_prize_list:
                category_prize_list[prize_data['box_category_id']] = []

            data                = {}
            data['item_type']   = prize_data['item_type']
            data['item_id']     = prize_data['item_id']
            data['quantity']    = prize_data['quantity']
            data['ratio']       = prize_data['ratio']
            category_prize_list[prize_data['box_category_id']].append(data)

        for key, prize_list in category_prize_list.items():

            random.shuffle(prize_list)
            max_ratio = sum(int(v['ratio']) for v in prize_list)
            rand_val = random.randint(0, max_ratio)

            border = 0
            for row in prize_list:
                border += row['ratio']
                if rand_val <= border:
                    del row['ratio']
                    ret_prize_list.append(row)
                    break

        return ret_prize_list


    def get_win_successive_prize(self, league_schedule_mst_id, class_id, victory_count):

        sql = 'select item_type, item_id, quantity from war_league_prize_victory_mst where war_league_schedule_mst_id = %s and war_class_mst_id = %s and victory_count = %s'
        self._db.execute(sql, (league_schedule_mst_id, class_id, victory_count))
        
        return list(self._db.fetchall())

    def get_lose_prize(self, league_schedule_mst_id, class_id):

        sql = 'select item_type, item_id, quantity from war_league_prize_lose_mst where war_league_schedule_mst_id = %s and war_class_mst_id = %s'
        self._db.execute(sql, (league_schedule_mst_id, class_id))
        
        return list(self._db.fetchall())

    # 連続勝利による報酬内容を取得する
    def get_successive_win_prize(self, victory_count):

        now = datetime.now()

        sql = 'select id, year, month, victory, item_type, item_id, quantity from war_victory_prize where year = %s and month = %s and victory = %s'
        self._db.execute(sql, (now.year, now.month, victory_count))
        
        return self._db.fetchall()

    # ユーザーの抗争結果を登録
    def insert_war_user_result(self, war_result_user_list):

        if len(war_result_user_list) == 0:
            return

        sql = 'insert into war_result_user (war_result_id, user_id, team_id, get_exp, sum_do_damage, use_item, is_result_shown, created) values (%s, %s, %s, %s, %s, %s, 0, %s)'
        self._db.executemany(sql, war_result_user_list)

    # war_result 登録情報を取得
    def get_war_result(self, war_id):

        sql = 'select * from war_result where id = %s'
        self._db.execute(sql, (war_id, ))

        return self._db.fetchone()

    # 抗争結果を更新
    def update_war_result(self, war_id, win_team_id, lose_team_id, win_user_list, lose_user_list, get_item, lose_item, win_team_hp_rate, lose_team_hp_rate, is_timeup):

        now_datetime = get_now_datetime()

        sql = 'update war_result set win_team_id = %s, lose_team_id = %s, win_active_member = %s, lose_active_member = %s, get_item = %s, get_lose_item = %s, win_team_hp_rate = %s, lose_team_hp_rate = %s, war_end_time = %s, is_timeup = %s where id = %s'
        self._db.execute(sql, (win_team_id, lose_team_id, ','.join(win_user_list), ','.join(lose_user_list), get_item, lose_item, win_team_hp_rate, lose_team_hp_rate, now_datetime, is_timeup, str(war_id)))

    # 抗争の詳細情報を登録
    def insert_war_detail(self, war_id, result_detail_data):

        sql = 'insert into war_result_detail (war_result_id, war_id, team_id, user_id, enemy_user_id, result, created) values (%s, %s, %s, %s, %s, %s, %s)'

        values = []
        for detail_data in result_detail_data:
            split = detail_data.split(',')
            team_id = split[0]
            user_id = split[1]
            enemy_user_id = split[2]
            result = split[3]
            result_datetime = split[4]

            values.append((war_id, '', team_id, user_id, enemy_user_id, result, result_datetime))

        self._db.executemany(sql, values)

    # 抗争によるチーム活動履歴を登録
    def insert_war_team_activity(self, win_team_data, lose_team_data):

        now_datetime = get_now_datetime()

        win_team_name = win_team_data['name']
        lose_team_name = lose_team_data['name']
        win_team_id = win_team_data['id']
        lose_team_id = lose_team_data['id']

        sql = 'insert into team_activity (team_id, user_id, category, message, created) values (%s, 0, %s, %s, %s)'
        values = []
        values.append((win_team_id, int(TeamActivityCategory.war_lose), u'抗争で {0} に勝利したぜ！'.format(lose_team_name), now_datetime))
        values.append((lose_team_id, int(TeamActivityCategory.war_win), u'抗争で {0} に敗北したぜ！'.format(win_team_name), now_datetime))

        self._db.executemany(sql, values)

    # リーグスケジュール情報を取得
    def get_league_schedule(self):

        now_datetime = get_now_datetime()

        query = 'select id, start_date, end_date from war_league_schedule_mst where %s between start_date and end_date and is_valid = 1'
        self._db.execute(query, (now_datetime, ))

        return self._db.fetchone()

    # ランキングデータを取得
    def get_ranking_data(self, war_schedule_mst_id, team_id):

        query = 'select * from war_team_status where team_id = %s and term_id = %s'
        self._db.execute(query, (team_id, war_schedule_mst_id) )

        return self._db.fetchone()

    # ランキングポイント更新
    def insert_ranking_data(self, war_schedule_mst_id, team_id, war_class_mst_id, point):

        now_datetime = get_now_datetime();
        query = 'insert into war_team_status (team_id, term_id, war_class_mst_id, point, updated, created) values(%s, %s, %s, %s, %s, %s)'
        self._db.execute(query, (team_id, war_schedule_mst_id, war_class_mst_id, point, now_datetime, now_datetime))

    # ランキングポイント更新
    def update_ranking_point(self, war_schedule_mst_id, team_id, point):
        
        now_datetime = get_now_datetime();
        query = 'update war_team_status set point = %s , updated = %s where team_id = %s and term_id = %s' 
        self._db.execute(query, (point, now_datetime, team_id, war_schedule_mst_id))

