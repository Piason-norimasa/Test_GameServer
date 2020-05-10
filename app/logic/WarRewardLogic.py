#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import math, random, json

from redis import Redis, ConnectionPool
from datetime import timedelta, datetime
from Utility import get_serial_date, get_now_datetime, convert_item_to_dict
from Define import ItemCategory

class WarRewardLogic(object):

    # 勝利/敗北チームユーザ場数定数
    MIN_USER_EXP                = 100
    WIN_TEAM_USER_EXP_CONSTANT  = 5.0
    LOSE_TEAM_USER_EXP_CONSTANT = 2.5

    # ユーザー経験値を取得
    def get_user_exp(self, ranking_point, is_win):

        base_exp = max(self.MIN_USER_EXP, ranking_point)

        if is_win:
            base_exp *= self.WIN_TEAM_USER_EXP_CONSTANT
        else:
            base_exp *= self.LOSE_TEAM_USER_EXP_CONSTANT

        return base_exp

    # 抗争勝利報酬メッセージ
    def get_win_present_message(self):
        return u'抗争勝利報酬'

    # 抗争参加報酬メッセージ
    def get_lose_present_message(self):
        return u'抗争参加賞'

    # 連勝報酬メッセージ
    def get_victory_prize_message(self, victory):
        return u'抗争{0}連勝！達成報酬'.format(victory)

    # 勝利チームの報酬データを取得
    def get_win_present_list(self, user_id_list, result_data):

        now_datetime = get_now_datetime()
        now_time = get_serial_date()
        present_list = []
        if len(user_id_list) == 0:
            return present_list

        prize_data_list = json.loads(result_data['get_item'])
        for user_id in user_id_list:
            for win_item in prize_data_list:
                present_list.append((user_id, int(win_item['item_type']), int(win_item['item_id']), self.get_win_present_message(), int(win_item['quantity']), now_time, now_datetime))

        return present_list

    # 敗北チームの報酬データを取得
    def get_lose_present_list(self, user_id_list, result_data):

        now_datetime = get_now_datetime()
        now_time = get_serial_date()

        present_list = []
        if len(user_id_list) == 0:
            return present_list

        prize_data_list = json.loads(result_data['get_lose_item'])
        for user_id in user_id_list:
            for lose_item in prize_data_list:
                present_list.append((user_id, int(lose_item['item_type']), int(lose_item['item_id']), self.get_lose_present_message(), int(lose_item['quantity']), now_time, now_datetime))

        return present_list

    # 連続勝利による報酬内容を取得
    def get_successive_victory_present_list(self, user_data_list, prize_data_list, victory_count):

        now_datetime = get_now_datetime()
        now_time = get_serial_date()
        present_list = []

        for prize in prize_data_list:
            for user_data in user_data_list:
                present_list.append((user_data['id'], prize['item_type'], prize['item_id'], self.get_victory_prize_message(victory_count), prize['quantity'], now_time, now_datetime))

        return present_list
