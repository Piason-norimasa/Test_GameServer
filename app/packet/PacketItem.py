#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import options

from PacketBase import Packet, PacketHandler
from RedisUserData import RedisUserData
from UserDataModel import UserDataModel
from ItemHistoryModel import ItemHistoryModel
from Define import ActionType, ConsumptionItem 
from AppServer import AppServer

class PacketItem(Packet):

    _hash_src = 'gzi'

    def __init__(self, data):

        self.item_category = int(data['item_category'])
        self.item_id       = int(data['item_id'])
        self.target_id     = int(data['target_id'])
        self._hash_code    = str(data['code'])

    def _create_data_hash(self):

        hash_value = self._hash_src
        hash_value += str(self.item_category)
        hash_value += str(self.item_id)
        hash_value += str(self.target_id)

        return super(PacketItem, self)._create_data_hash(hash_value)


class PacketItemHandler(PacketHandler):

    def __init__(self, socket_handler, data):

        super(PacketItemHandler, self).__init__(socket_handler, data)

    def _execute(self):

        # リクエストパラメーターチェック
        packet = PacketItem(self._data)
        if not packet.is_validate_hash():
            return False

        # アイテム使用以外のアクションが来た場合は不正パケットとみなす
        if packet.item_category not in (ActionType.use_item_hp_heal, ActionType.use_item_dead_heal, ActionType.use_item_skill_heal):
            return False

        user_id       = self._socket_handler._user_id
        war_id        = self._socket_handler._war_id
        team_id       = self._socket_handler._team_id
        enemy_team_id = self._socket_handler._enemy_team_id
        item_id       = int(packet.item_id)

        redis_user = RedisUserData()

        app_instance = AppServer()
        db_master  = app_instance.get_db_connection('master')
        cur_master = db_master.cursor()
        db_log     = app_instance.get_db_connection('log')
        cur_log    = db_log.cursor()

        user_data_model = UserDataModel(cur_master)
        item_log_model = ItemHistoryModel(cur_log)

        # アイテム所持数管理
        possession_item_list = user_data_model.get_consumption_item(user_id)
        item_manager = ItemUseManager(possession_item_list, packet.item_category, packet.item_id)

        # アイテムを所持していない場合は処理終了
        item_num_ok = item_manager.is_enable_consumption_item_quantity() 
        use_item_id = item_manager.get_use_item_id()
        heal_effect = item_manager.get_heal_effect()
        rest_hp = 0
        heal_value = 0
        res_status = ''

        # アイテムの使用状況情報を取得
        item_use_info_list = redis_user.get_item_data_info(war_id, team_id, user_id)
        item_use_info = item_use_info_list[int(packet.item_id)]
        item_use_num = int(item_use_info['use_num'])

        if int(item_use_info['use_num_limit']) - int(item_use_info['use_num']) <= 0:
            res_status = 'limit'

        if res_status == '':
            if item_num_ok:
                #### todo:: アイテム効果発動処理(redis) is_dead確認後、問題なければ使用
                redis_result_data = redis_user.use_item(war_id, team_id, user_id, packet.item_category, use_item_id, item_id, packet.target_id, heal_effect)
                res_status = redis_result_data['status']

                if res_status == 'ok':
                    rest_hp     = int(redis_result_data['rest_hp'])
                    heal_value  = int(redis_result_data['heal_value'])
                    item_use_num = item_use_num + 1
            else:
                res_status = 'lack'

        # 返却データ作成
        use_item_result_data = {
            'res': res_status, # 結果('ok':成功, 'dead':気絶中のため失敗)
            'team_id': team_id,
            'user_id': user_id,
            'item_category': packet.item_category,
            'item_id': use_item_id,
            'item_count':item_manager.get_item_quantity(use_item_id) - 1,
            'item_use_remain':int(item_use_info['use_num_limit']) - int(item_use_num),
            'target_id': packet.target_id,
            'value': heal_value,
            'rest_hp': rest_hp,
        }

        if res_status == 'ok':

            # 返却データ送信
            self._socket_handler.send_message({
                'war_id': war_id,
                'team_id': team_id,
                'item': use_item_result_data,
            })

            self._socket_handler.send_message({
                'war_id': war_id,
                'team_id': enemy_team_id,
                'item': use_item_result_data,
            })

            # DB更新処理で重そうなのでpacket飛ばした後に更新処理を行う
            user_data_model.use_consumption_item(user_id, item_manager.get_use_item_id())
            item_log_model.add_data(user_id, use_item_id, -1)

            db_master.commit()
            db_log.commit()
            cur_master.close()
            cur_log.close()
        else:

            # アイテム使用失敗の旨を自分にのみ通知
            self._socket_handler.send_message_to_myself({
                'war_id': war_id,
                'team_id': team_id,
                'item': use_item_result_data,
            })

            cur_master.close()
            cur_log.close()
        return True


class ItemUseManager(object):

    def __init__(self, possession_item_list, item_category, item_id):
        self.possession_item_list = possession_item_list

        # 抗争内で使用するアイテムカテゴリ
        self.use_war_item_category = item_category

        # 抗争内で使用するアイテムID
        self.use_war_item_id = item_id

        # 使用するアイテムの情報を管理アイテムIDに変換する(publicのアイテムIDが来ることを想定)
        self.use_consumption_item_id = self.__get_consumption_item_id(item_category, item_id)

        # 使用するアイテムの共用時のアイテムIDを記憶
        self.use_public_item_id = self.use_consumption_item_id % 100

        # 使用するアイテムのてめぇ専用時のアイテムIDを記憶
        self.use_private_item_id = self.use_public_item_id + 100

        # 使用するアイテムの所持数を記憶
        public_item_quantity, private_item_quantity = self.__get_consumption_item_quantity()
        self.selected_item_quantity_public = public_item_quantity
        self.selected_item_quantity_private = private_item_quantity

    def is_enable_consumption_item_quantity(self):
        return (self.selected_item_quantity_public + self.selected_item_quantity_private) > 0

    def get_item_quantity(self, item_id):
        if item_id >= 100:
            return self.selected_item_quantity_private

        return self.selected_item_quantity_public

    def get_use_item_id(self):
        if self.__is_use_private():
            return self.use_private_item_id
        return self.use_public_item_id

    def get_heal_effect(self):
        item_id = self.get_use_item_id()
        if item_id == ConsumptionItem.small or item_id == ConsumptionItem.small_private:
            return 800
        return 2500

    def __get_consumption_item_id(self, item_category, public_item_id):
        if item_category == ActionType.use_item_hp_heal:
            if public_item_id in (ConsumptionItem.small, ConsumptionItem.big):
                return public_item_id
        elif item_category == ActionType.use_item_dead_heal:
            return ConsumptionItem.aed
        elif item_category == ActionType.use_item_skill_heal:
            return ConsumptionItem.skill
        else:
            pass

        assert False, "undefine item selected"

    def __get_consumption_item_quantity(self):
        datas = [x for x in self.possession_item_list if x['item_id'] % 100 == self.use_public_item_id]

        public_item_quantity = [x['quantity'] for x in datas if x['item_id'] == self.use_public_item_id][0]
        private_item_quantity = [x['quantity'] for x in datas if x['item_id'] == self.use_private_item_id][0]

        return public_item_quantity, private_item_quantity

    def __is_use_private(self):
        if self.selected_item_quantity_private > 0:
            return True
        return False

