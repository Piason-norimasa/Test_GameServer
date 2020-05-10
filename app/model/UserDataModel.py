#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

from BaseModel import BaseModel
from datetime import timedelta, datetime

from Utility import get_now_datetime, get_serial_date
from Define import ConsumptionItem
from UserLogic import UserLogic

class UserDataModel(BaseModel):

    def __init__(self, db):

        super(UserDataModel, self).__init__(db)

    # チームメンバーのHPを更新
    def update_lose_users_hp(self, team_id, hp):

        sql = 'update user set hp = %s, hp_recovery_time = %s, is_dead = 0 where team_id = %s'

        return self._db.execute(sql, (hp, get_serial_date(), team_id))

    # 特定ユーザーのHPを更新する
    def update_win_users_hp(self, user_hp_list):

        if user_hp_list is None or len(user_hp_list) == 0:
            return

        sql = 'update user set hp = hp_max * %s , hp_recovery_time = %s, is_dead = 0 where id = %s'
        self._db.executemany(sql, user_hp_list)

    # ユーザーのプロテイン効果情報を取得
    def get_enable_protein_effect(self, user_id_list):

        user_id_count = len(user_id_list)
        if user_id_count == 0:
            return

        now_time = get_serial_date()

        format_strings = ','.join(['%s'] * user_id_count)
        sql = 'select id, user_id, effect, open_time, end_time from protein_status where user_id in (' + format_strings + ') and open_time <= %s and end_time >= %s'

        self._db.execute(sql, tuple(user_id_list) + (now_time, now_time))
        
        return self._db.fetchall()

    # プロテイン効果を登録
    def insert_protein_effect(self, insert_data_list):

        if len(insert_data_list) == 0:
            return

        sql = 'insert into protein_status (user_id, open_time, end_time, created) values (%s, %s, %s, %s)'
        self._db.executemany(sql, insert_data_list)

    # ユーザーIDリストからデータ取得
    def get_user_data_list(self, user_id_list):

        sql = '''
            SELECT id, lv FROM user
            WHERE
                id in (%s)
        ''' % ( ','.join(['%s' for user_id in user_id_list]))

        self._db.execute(sql, tuple(user_id_list,))

        return self._db.fetchall()

    def add_exp_to_user(self, user_id, user_exp):

        now_datetime = get_now_datetime()

        sql = '''
            insert into pending_exp
                (user_id, exp, updated, created)
            values
                (%s, %s, %s, %s)
            on duplicate key update
                exp=exp+%s,
                updated=%s
        '''
        # 場数付与
        self._db.execute(sql, (user_id, user_exp, now_datetime, now_datetime, user_exp, now_datetime))

############################################################

    def get_consumption_item(self, user_id):
        possession_item_list = []

        sql = 'select hp, hp_max, is_dead, hp_recovery_time, consumption_item_small, consumption_item_big from user where id = %s'
        self._db.execute(sql, (user_id,))
        now_data = self._db.fetchone()

        item_small = now_data['consumption_item_small']
        item_big = now_data['consumption_item_big']

        possession_item_list.append({'item_id': ConsumptionItem.small, 'quantity': item_small})
        possession_item_list.append({'item_id': ConsumptionItem.big, 'quantity': item_big})

        # 自分用回復アイテムの所持数を取得する
        item_small_private = 0
        item_big_private = 0
        now_private_consumption_item = self.__get_private_consumption_item(user_id)
        if now_private_consumption_item:
            for private_item in now_private_consumption_item:
                if private_item['item_consumption_id'] == ConsumptionItem.small_private:
                    item_small_private = private_item['quantity']
                elif private_item['item_consumption_id'] == ConsumptionItem.big_private:
                    item_big_private = private_item['quantity']

        possession_item_list.append({'item_id': ConsumptionItem.small_private, 'quantity': item_small_private})
        possession_item_list.append({'item_id': ConsumptionItem.big_private, 'quantity': item_big_private})
    
        # AEDアイテムを取得、、、
        query = 'select * from item_consumption_possession where user_id = %s and item_consumption_id in (%s, %s)'
        self._db.execute(query, (user_id, int(ConsumptionItem.aed), int(ConsumptionItem.aed_private)))
        aed_data_list = self._db.fetchall()
        aed_private_num = 0
        aed_public_num = 0
        for aed_data in aed_data_list:
            if aed_data['item_consumption_id'] == ConsumptionItem.aed:
                aed_public_num = aed_data['quantity']
            elif aed_data['item_consumption_id'] == ConsumptionItem.aed_private:
                aed_private_num = aed_data['quantity']

        possession_item_list.append({'item_id': ConsumptionItem.aed, 'quantity': aed_public_num})
        possession_item_list.append({'item_id': ConsumptionItem.aed_private, 'quantity': aed_private_num})

        return possession_item_list

    def __get_private_consumption_item(self, user_id):

        self._db.execute('''
            SELECT
                id,
                item_consumption_id,
                quantity
            FROM
                item_consumption_possession
            WHERE
                user_id = %s AND
                delete_flg = 0
        ''', (user_id,))
        return self._db.fetchall()

    def use_consumption_item(self, user_id, item_id):

        if ConsumptionItem.small == item_id:
            self._db.execute('update user set consumption_item_small = consumption_item_small - 1 where id = %s', (user_id,))
        elif ConsumptionItem.big == item_id:
            self._db.execute('update user set consumption_item_big = consumption_item_big - 1 where id = %s', (user_id,))
        else:
            self._db.execute('update item_consumption_possession set quantity = quantity - 1 where user_id = %s and item_consumption_id = %s', (user_id, item_id))

        # アイテムを使用することによるミッション情報を更新
        user_logic = UserLogic()
        user_logic.update_mission_status(user_id, self._db, 1, condition_type = 'use_heal')

        # アイテムを使用することによるタイトルを更新
        user_logic.update_user_title(user_id, self._db, None)
