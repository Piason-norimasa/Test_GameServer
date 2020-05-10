#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import threading
import tornado
from tornado import websocket, web, ioloop, httpclient
import tornado.options
from tornado.options import define, options

import AppServer
import random
from RedisWarData import RedisWarData
from Utility import get_serial_date
from WarResultLogic import WarResultLogic

# 定期実行関数
def fixed_update():
    
    __monitor_war_end()
    __monitor_ws_handler()

# socket監視
def __monitor_ws_handler():

    app_instance = AppServer.AppServer()
    app_instance.logging_websocket_client_count()

# 抗争終了監視
def __monitor_war_end():
    
    app_instance = AppServer.AppServer()
    redis_war_data = RedisWarData()
    now_time = get_serial_date()
    del_war_id_list = []

    # メインループ処理を修正
    for war_id, ws_client_list in app_instance.get_ws_all_client().items():

        war_time = redis_war_data.get_war_end_time(war_id)
        if war_time is None:

            del_war_id_list.append(war_id)
        elif now_time >= war_time['end'] + 30:

            del_war_id_list.append(war_id)

            # 抗争終了状態で正常に終わっていなければ終了処理を実行させる
            war_data = redis_war_data.get_war_state_data(war_id)
            if war_data['is_end'] == False:

                matching_data = redis_war_data.get_matching_team(war_id)
                logging.info('force execute result of war for timeup  war_id:' + str(war_id) + ' matching_team(' + str(matching_data['team_1']) + ',' + str(matching_data['team_2']) + ')' )

                result = redis_war_data.timeup_judge_win_team(war_id, matching_data['team_1'], matching_data['team_2'], options.redis_war_data_expire, random.choice(('0', '1')))
                win_team_id     = result['win']
                lose_team_id    = result['lose']
                enemy_count     = result['enemy_count']
                finish_attack   = result['finish_attack']

                if result['type'] == 'timeup':

                    war_result_logic = WarResultLogic()
                    members = redis_war_data.get_end_member(war_id, win_team_id, lose_team_id)
                    war_result_logic.regist_war_result(war_id, win_team_id, lose_team_id, enemy_count, members['win'], members['lose'], is_timeup = 1)

    # 終了済みのものを削除
    for war_id in del_war_id_list:
        
        war_ws_dict = app_instance.get_ws_all_client()

        # Handlerを削除
        for ws_handle in war_ws_dict[war_id]:
            ws_handle.close()
            war_ws_dict[war_id].remove(ws_handle)

        del war_ws_dict[war_id]
        logging.info('complete delete war_id:' + str(war_id))

