#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import define, options
import MySQLdb

from datetime import timedelta, datetime
import math, random, json

from RedisWarData import RedisWarData
from RedisUserData import RedisUserData
from Utility import get_serial_date, get_now_datetime, convert_item_to_dict

import AppServer
from CampaignModel import CampaignModel
from TeamDataModel import TeamDataModel
from WarDataModel import WarDataModel
from WarLogModel import WarLogModel
from PresentDataModel import PresentDataModel
from UserDataModel import UserDataModel

from WarRewardLogic import WarRewardLogic
from WarCampaignLogic import WarCampaignLogic

class WarResultLogic(object):

    # 抗争結果を各ユーザの抗争情報に登録する
    def regist_war_result(self, war_id, win_team_id, lose_team_id, enemy_count, win_members, lose_members, is_timeup):

        app_instance = AppServer.AppServer()

        db_master   = app_instance.get_db_connection('master')
        cur_master  = db_master.cursor()
        db_log      = app_instance.get_db_connection('log')
        cur_log     = db_log.cursor()

        campaign_model      = CampaignModel(cur_master)
        war_data_model      = WarDataModel(cur_master)
        team_data_model     = TeamDataModel(cur_master)
        present_data_model  = PresentDataModel(cur_master)
        user_data_model     = UserDataModel(cur_master)
        war_log_model       = WarLogModel(cur_log)

        redis_war_data          = RedisWarData()
        redis_war_by_app_pool   = RedisWarData(app_instance.get_app_pool())
        redis_user_data         = RedisUserData()

        war_reward_logic    = WarRewardLogic()
        war_campaign_logic  = WarCampaignLogic()

        # 勝利チーム、敗北チームのチーム情報を取得する
        team_data = team_data_model.get_team_data(win_team_id, lose_team_id)
        win_team_data = lose_team_data = {}
        if int(team_data[0]['id']) == int(win_team_id):
            win_team_data = team_data[0]
            lose_team_data = team_data[1]
        else:
            win_team_data = team_data[1]
            lose_team_data = team_data[0]

        win_team_class_id = win_team_data['war_class_id']
        lose_team_class_id = lose_team_data['war_class_id']
        is_change_class = False
        tmp_win_team_class_id = win_team_class_id
        tmp_lose_team_class_id = lose_team_class_id

        # 入れ替え戦時において、勝敗結果によって階級の入れ替え発生
        war_result_data = war_data_model.get_war_result(war_id)
        if war_result_data['is_war_for_shuffle']:

            if win_team_data['war_class_id'] < lose_team_data['war_class_id']:
                win_team_class_id = lose_team_data['war_class_id']
                lose_team_class_id = win_team_data['war_class_id']
                is_change_class = True

            # 抗争入れ替え戦結果をログ保存
            war_log_model.insert_war_shuffle_result_log(war_result_data['war_league_schedule_mst_id'],
                                                        war_id,
                                                        win_team_id,
                                                        tmp_win_team_class_id,
                                                        win_team_class_id,
                                                        lose_team_id,
                                                        tmp_lose_team_class_id,
                                                        lose_team_class_id)

        matching_war_id         = war_result_data['war_id']
        matching_former_team_id = matching_war_id[0:9]
        matching_later_team_id  = matching_war_id[9:9]
        win_team_ranking_point  = 0
        lose_team_ranking_point = 0

        # 抗争結果ランキングポイントを取得
        if int(matching_former_team_id) == int(win_team_id):
            win_team_ranking_point = war_result_data['former_win_point']
            lose_team_ranking_point = war_result_data['latter_lose_point']
        else:
            win_team_ranking_point = war_result_data['latter_win_point']
            lose_team_ranking_point = war_result_data['former_lose_point']

        # ランキングポイント更新
        win_team_point = self.__add_ranking_point(war_data_model, team_data_model, war_result_data['war_league_schedule_mst_id'], win_team_id, win_team_ranking_point)
        lose_team_point = self.__add_ranking_point(war_data_model, team_data_model, war_result_data['war_league_schedule_mst_id'], lose_team_id, lose_team_ranking_point)

        # チームデータ更新
        win = win_team_data['win'] + 1
        team_data_model.update_team_status(win_team_id, (win_team_data['win'] + 1), win_team_class_id)
        team_data_model.update_team_as_war_lose(lose_team_id, lose_team_class_id)

        # チーム活動履歴を登録
        war_data_model.insert_war_team_activity(win_team_data, lose_team_data)

        # プレゼントデータを取得
        win_prize_list      = war_data_model.get_win_prize(war_result_data['war_league_schedule_mst_id'], tmp_win_team_class_id)
        lose_prize_list     = war_data_model.get_lose_prize(war_result_data['war_league_schedule_mst_id'], tmp_lose_team_class_id)
        result_data         = self.__get_war_result_data(win_team_id, lose_team_id, win_team_data['lv'], is_change_class, win_team_ranking_point, lose_team_ranking_point, win_prize_list, lose_prize_list)
        result_data['war_league_schedule_mst_id'] = war_result_data['war_league_schedule_mst_id']
        result_data['before_win_team_class_id'] = tmp_win_team_class_id
        result_data['win_team_class_id'] = win_team_class_id

        win_present_list    = war_reward_logic.get_win_present_list(win_members, result_data)
        lose_present_list   = war_reward_logic.get_lose_present_list(lose_members, result_data)
        present_list        = win_present_list + lose_present_list

        # 連勝報酬あればプレゼント
        win_team_data = team_data_model.get_team_data_by_id(win_team_id)
        victory = int(win_team_data['win_straight_count'])
        prize_list = war_data_model.get_win_successive_prize(war_result_data['war_league_schedule_mst_id'], tmp_win_team_class_id, victory)

        if len(prize_list) > 0:

            win_team_full_members = team_data_model.get_user_id_list_by_team_id(win_team_id)
            successive_win_present_list = war_reward_logic.get_successive_victory_present_list(win_team_full_members, prize_list, victory)
            present_list = present_list + successive_win_present_list
 
        # プレゼント報酬登録
        present_data_model.insert_present_data_list(present_list)

        # 連勝数の保存
        war_log_model.insert_war_victory_log(war_id, win_team_id, victory)

        # TODO: 場数計算(修正必須）
        win_team_user_exp   = war_reward_logic.get_user_exp(win_team_point, True)
        lose_team_user_exp  = war_reward_logic.get_user_exp(lose_team_point, False)
        exp_up_ratio        = 1.0

        # キャンペーン情報を取得
        campaigns = campaign_model.get_exp_campaign_data()
        campaigns = dict([ (row['name'], row) for row in campaigns])
        other_campaigns = campaign_model.get_beginner_exp_campaign_data()

        # 場数アップキャンペーン
        if 'exp_up' in campaigns:
            exp_up_ratio *= war_campaign_logic.get_exp_up_campaign_ratio()

        # プロテイン効果取得
        all_members = win_members + lose_members
        protein_enable_status_list = user_data_model.get_enable_protein_effect(all_members)
        user_protein_status = dict([ (row['user_id'], float(row['effect'])) for row in protein_enable_status_list])

        # 初心者ブーストキャンペーン
        user_data_list = user_data_model.get_user_data_list(all_members)
        user_lv_list = dict([ (row['id'], int(row['lv'])) for row in user_data_list ])
        
        # ユーザ場数付与
        war_result_user_list = []

        loop_data = [
            (win_team_user_exp, win_team_id, win_members),
            (lose_team_user_exp, lose_team_id, lose_members)
        ]

        now_datetime = get_now_datetime()
        for base_exp, team_id, member_list in loop_data:
            for user_id in member_list:
                user_id = int(user_id)

                # 場数アップ効果
                user_exp_up_ratio = exp_up_ratio
                if user_id in user_protein_status:
                    user_exp_up_ratio *= user_protein_status[user_id]

                # 初心者ブーストキャンペーン効果
                for begin_list in other_campaigns:
                    f = begin_list["setting_value"]
                    row = f.split(",")
                    if int(row[0]) <= user_lv_list[user_id] and int(row[1]) > user_lv_list[user_id]:
                        user_exp_up_ratio *= float(row[2])
                        break

                # 場数
                user_exp = int(math.floor(base_exp * user_exp_up_ratio))
                user_data_model.add_exp_to_user(user_id, user_exp)

                # ユーザー貢献度情報を取得
                contribution = redis_user_data.get_user_contribution(war_id, team_id, user_id)

                # 個人抗争結果リストに追加
                war_result_user_list.append( (war_id, user_id, team_id, user_exp, contribution['sum_do_damage'], contribution['use_item'], now_datetime) )

        # ユーザ場数付与履歴書き込み(結果画面用)
        war_data_model.insert_war_user_result(war_result_user_list)

        win_team_hp_list    = self.__get_users_hp_data_list(war_id, win_team_id, win_members)
        lose_team_hp_list   = self.__get_users_hp_data_list(war_id, lose_team_id, lose_members)
        win_team_hp_max     = sum(int(k['hp_max']) for k in win_team_hp_list)
        win_team_hp_max     = 1 if win_team_hp_max == 0 else win_team_hp_max
        lose_team_hp_max    = sum(int(k['hp_max']) for k in lose_team_hp_list)
        lose_team_hp_max    = 1 if lose_team_hp_max == 0 else lose_team_hp_max

        win_team_hp_rate    = float(sum(int(v['hp']) for v in win_team_hp_list)) / win_team_hp_max
        lose_team_hp_rate   = float(sum(int(v['hp']) for v in lose_team_hp_list)) / lose_team_hp_max

        # チーム全員のHPを更新(敗北チームはHP０に), 勝利チームは残りHPから算出
        user_data_model.update_lose_users_hp(lose_team_id, 1)
        hp_update_query_list = self.__hp_update_query_list(win_team_hp_list)
        user_data_model.update_win_users_hp(hp_update_query_list)

        # 抗争履歴登録
        war_data_model.update_war_result(war_id, 
                                        win_team_id, 
                                        lose_team_id, 
                                        win_members, 
                                        lose_members, 
                                        result_data['get_item'], 
                                        result_data['get_lose_item'],
                                        win_team_hp_rate,
                                        lose_team_hp_rate,
                                        is_timeup)

        # 抗争参加ユーザ場数アップキャンペーン
        war_campaign_data = campaign_model.get_war_exp_campaign_data()
        if war_campaign_data is not None:
            war_campaign_logic.set_user_exp_up_campaign(user_data_model, win_members, True)
            war_campaign_logic.set_user_exp_up_campaign(user_data_model, lose_members, False)

        # DB コミット処理
        db_master.commit()
        db_log.commit()

        # redis 更新
        redis_war_by_app_pool.update_war_result(win_team_id, lose_team_id, win_members, lose_members, result_data, win)
        redis_war_data.finish(war_id, options.redis_war_data_expire)

    # HPデータリスト
    def __get_users_hp_data_list(self, war_id, team_id, user_id_list):

        redis_user = RedisUserData()
        now = get_serial_date()
        ret_list = []

        for user_id in user_id_list:
            hp_data = redis_user.get_user_hp(war_id, team_id, user_id)
            hp_data['user_id'] = user_id
            ret_list.append(hp_data)

        return ret_list

    # 勝利チームHP更新用のデータを更新する
    def __hp_update_query_list(self, hp_data_list):

        query_param_list = []

        for hp_data in hp_data_list:

            hp_rate = float(hp_data['hp']) / float(hp_data['hp_max'])
            if hp_rate > 1.0:
                hp_rate = 1.0
            elif hp_rate < 0.0:
                hp_rate = 0.0
            query_param = (hp_rate, get_serial_date(), hp_data['user_id'])
            query_param_list.append(query_param)

        return query_param_list

    # 抗争の結果情報を取得
    def __get_war_result_data(self, win_team_id, lose_team_id, win_team_lv, is_change_class, win_team_ranking_point, lose_team_ranking_point, win_prize_list, lose_prize_list):

        # チームレベルで補正
        result_data = {
            'win_team_id':              win_team_id,
            'lose_team_id':             lose_team_id,
            'is_change_class':          is_change_class,
            'get_item':                 json.dumps(win_prize_list),
            'get_lose_item':            json.dumps(lose_prize_list),
            'win_team_ranking_point':   win_team_ranking_point,
            'lose_team_ranking_point':  lose_team_ranking_point,
        }

        return result_data

    # 抗争ポイントを追加
    def __add_ranking_point(self, model_war, model_team, war_league_schedule_mst_id, team_id, add_point):

        point = 0

        ranking_team_data = model_war.get_ranking_data(war_league_schedule_mst_id, team_id)
        if ranking_team_data is None:

            team_data = model_team.get_team_data_by_id(team_id)
            if team_data is not None:
                point = max(0, add_point)
                model_war.insert_ranking_data(war_league_schedule_mst_id, team_id, team_data['war_class_id'], point)
        else:
            point = max(0, ranking_team_data['point'] + add_point)
            model_war.update_ranking_point(war_league_schedule_mst_id, team_id, point)

        return point
