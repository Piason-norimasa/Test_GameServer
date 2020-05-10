#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import options

from WebApi import WebApi
from RedisWarData import RedisWarData
from Utility import get_serial_date
from Define import TeamPosition

class WebApiGetData(WebApi):

    def __init__(self, request_handler, data):

        super(WebApiGetData, self).__init__(request_handler, data)

    # パラメーターチェック
    def _is_validate_parameters(self, data):

        if 'war_id' not in data or data['war_id'] is None:
            return False
        if 'team_id' not in data or data['team_id'] is None:
            return False

        hash_src = 'etd'
        hash_src += str(data['war_id'])
        hash_src += str(data['team_id'])

        # check hacking
        if data['code'] != self._get_hash_code(hash_src):
            return False

        return True

    def _execute(self):

        data = self._data

        # リクエストパラメーターチェック
        if self._is_validate_parameters(data) == False:
            self._request_handler.response({ 'res': False, 'status': 'hacking' })
            return

        war_id = data['war_id']
        team_id = data['team_id']

        if not war_id or not team_id:
            self._request_handler.response({ 'res': False, 'status': 'error' })
            return

        # 敵チームを取得
        redis_war = RedisWarData()
        enemy_team_data = redis_war.get_enemy_data(war_id, team_id, get_serial_date())

        if enemy_team_data['type'] == 'error':
            self._request_handler.response({ 'res': False, 'status': enemy_team_data['status'] })
            return

        enemy_user_list = enemy_team_data['data']['parent']
        enemy_team_id = enemy_user_list[0]['team_id']

        # 自チーム情報を取得
        myself_team_data = redis_war.get_enemy_data(war_id, enemy_team_id, get_serial_date())
        if myself_team_data['type'] == 'error':
            self._request_handler.response({ 'res': False, 'status': myself_team_data['status'] })
            return

        self._request_handler.response({ 'res': True, 'data': self.__convert_client_response(myself_team_data['data'], enemy_team_data['data']) })

    # クライアントレスポンスデータに変換
    def __convert_client_response(self, myself_team_data, enemy_team_data):

        # ユーザーデータからスキル情報を取得
        def get_skill_data(user_data):

            skill_data_list = []
            for i in range(3):
                skill_data = {}
                skill_data['SkillId'] = int(user_data['skill' + str(i+1) + '_id'])
                skill_data['MaxLv'] = int(user_data['skill' + str(i+1) + '_level_max'])
                skill_data['Percent'] = int(user_data['skill' + str(i+1) + '_gauge'])

                skill_data_list.append(skill_data)

            return skill_data_list

        # ユーザーデータからアイテム情報取得
        def get_item_data(user_data):

            item_data_list = []

            # small アイテム
            item_data = {}
            item_data['ItemMstId']      = 0
            item_data['RemainUseNum']   = int(user_data['item0_use_num_limit']) - int(user_data['item0_use_num'])
            item_data_list.append(item_data)

            # big アイテム
            item_data = {}
            item_data['ItemMstId']      = 1
            item_data['RemainUseNum']   = int(user_data['item1_use_num_limit']) - int(user_data['item1_use_num'])
            item_data_list.append(item_data)

            # AED アイテム
            item_data = {}
            item_data['ItemMstId']      = 4
            item_data['RemainUseNum']   = int(user_data['item4_use_num_limit']) - int(user_data['item4_use_num'])
            item_data_list.append(item_data)

            return item_data_list

        # ユーザーの役職IDを取得
        def get_post_id(user_data):
            if int(user_data['team_leader_id']) == int(user_data['id']):
                return int(TeamPosition.leader)
            if user_data['team_sub_leader_id'] != 'None' and int(user_data['team_sub_leader_id']) == int(user_data['id']):
                return int(TeamPosition.sub_leader)
            return -1

        myself_user_data_list = []
        for user_data in myself_team_data['parent']:

            have_enemy_list = []
            for enemy_user_data in enemy_team_data['parent']:
                if int(enemy_user_data['target_user_id']) == int(user_data['id']):
                    have_enemy_list.append(int(enemy_user_data['id']))

            client_user_data                = {}
            client_user_data['UserId']      = int(user_data['id'])
            client_user_data['UserName']    = user_data['name']
            client_user_data['Post']        = get_post_id(user_data)
            client_user_data['Hp']          = int(float(user_data['hp']))
            client_user_data['HpMax']       = int(user_data['hp_max'])
            client_user_data['IsDead']      = False if user_data['is_dead'] == '0' else True
            client_user_data['AvatarThumbnailUpdated'] = user_data['avatar_thumbnail_updated']
            client_user_data['BikeThumbnailUpdated'] = user_data['bike_thumbnail_updated']
            client_user_data['Skill']       = get_skill_data(user_data)
            client_user_data['Item']        = get_item_data(user_data)
            client_user_data['HaveEnemyIds'] = have_enemy_list

            myself_user_data_list.append(client_user_data)

        team_name = ""
        team_id = 0
        enemy_user_data_list = []
        for user_data in enemy_team_data['parent']:

            have_enemy_list = []
            for myself_user_data in myself_team_data['parent']:
                if int(myself_user_data['target_user_id']) == int(user_data['id']):
                    have_enemy_list.append(int(myself_user_data['id']))

            team_name = user_data['team_name']
            team_id = user_data['team_id']

            client_user_data                = {}
            client_user_data['UserId']      = int(user_data['id'])
            client_user_data['UserName']    = user_data['name']
            client_user_data['Post']        = get_post_id(user_data)
            client_user_data['Hp']          = int(float(user_data['hp']))
            client_user_data['HpMax']       = int(user_data['hp_max'])
            client_user_data['IsDead']      = False if user_data['is_dead'] == '0' else True
            client_user_data['AvatarThumbnailUpdated'] = user_data['avatar_thumbnail_updated']
            client_user_data['BikeThumbnailUpdated'] = user_data['bike_thumbnail_updated']
            client_user_data['Skill']       = get_skill_data(user_data)
            client_user_data['Item']        = get_item_data(user_data)
            client_user_data['HaveEnemyIds']= have_enemy_list

            enemy_user_data_list.append(client_user_data)

        ret = {}
        ret['SelfTeamMembers']  = myself_user_data_list
        ret['EnemyTeamMembers'] = enemy_user_data_list
        ret['EnemyTeamId']      = int(team_id)
        ret['EnemyTeamName']    = team_name

        return ret

