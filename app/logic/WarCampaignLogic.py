#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

from datetime import timedelta, datetime
from CampaignModel import CampaignModel
from UserDataModel import UserDataModel
from Utility import get_serial_date, get_now_datetime

class WarCampaignLogic(object):

    # 場数アップキャンペーン増加割合
    __war_exp_up_campaign_ratio     = 2.0
    
    __war_win_exp_up_campaign_time  = 1800
    __war_lose_exp_up_campaign_time = 600

    # 抗争キャンペーン時の場数アップ
    def get_exp_up_campaign_ratio(self):

        return self.__war_exp_up_campaign_ratio

    # 抗争参加ユーザ場数アップキャンペーン
    def set_user_exp_up_campaign(self, user_data_model, user_ids, is_win):

        now_datetime    = get_now_datetime()
        now_time        = get_serial_date()

        using_data = user_data_model.get_enable_protein_effect(user_ids)

        effect_time = 0
        if is_win:
            effect_time = self.__war_win_exp_up_campaign_time
        else:
            effect_time = self.__war_lose_exp_up_campaign_time

        using_ids = []
        insert_data = []

        # 既に使用中のユーザは終了直後に発動
        for row in using_data:
            using_ids.append(int(row['user_id']))
            insert_data.append([row['user_id'], row['end_time'], row['end_time'] + effect_time, now_date])

        for user_id in user_ids:
            if int(user_id) in using_ids:
                continue
            insert_data.append([user_id, now_time, now_time + effect_time, now_datetime])

        # プロテイン効果を登録
        user_data_model.insert_protein_effect(user_ids, insert_data)
