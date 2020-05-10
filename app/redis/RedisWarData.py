#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import tornado.options
from tornado.options import define, options

from redis import Redis, ConnectionPool
from RedisBaseData import RedisBaseData
import msgpack
from datetime import timedelta, datetime

from Utility import get_serial_date

class RedisWarData(RedisBaseData):

    def __init__(self, connection_pool = None):

        super(RedisWarData, self).__init__(connection_pool)

    # 抗争マッチングチーム
    def get_matching_team(self, war_id):

        data = self._redis.hmget('{0}:matching'.format(war_id), 'team_1', 'team_2')
        ret_data            = {}
        ret_data['team_1']  = int(data[0])
        ret_data['team_2']  = int(data[1])

        return ret_data

    # 抗争時間を取得
    def get_war_end_time(self, war_id):

        war_end_time = self._redis.hmget('{0}:time'.format(war_id), 'start', 'end')
        if war_end_time[0] is None:
            return None

        ret_data            = {}
        ret_data['start']   = int(war_end_time[0])
        ret_data['end']     = int(war_end_time[1])

        return ret_data

    def get_war_state_data(self, war_id):

        war_data                            = self._redis.hmget('{0}:war_data'.format(war_id), 'is_end', 'is_end_countdown', 'countdown_start_time', 'win_team_id', 'lose_team_id')
        ret_data                            = {}
        ret_data['is_end']                  = True if war_data[0] == '1' else False
        ret_data['is_end_countdown']        = True if war_data[1] == '1' else False
        ret_data['countdown_start_time']    = int(war_data[2])
        ret_data['win_team_id']             = int(war_data[3])
        ret_data['lose_team_id']            = int(war_data[4])
        
        return ret_data

    # 抗争の詳細情報を取得
    def get_war_detail_data(self, war_id):

        result_detail_data = self._redis.smembers('war:{0}:detail'.format(war_id))

        return result_detail_data

    # 抗争結果による更新
    def update_war_result(self, win_team_id, lose_team_id, win_user_list, lose_user_list, result_data, victory_count):

        pipe = self._redis.pipeline()

        # 抗争結果を登録する
        for user_id in win_user_list:
            key = 'user:{0}:war_result'.format(user_id)
            pipe.hmset(key, result_data)

        for user_id in lose_user_list:
            key = 'user:{0}:war_result'.format(user_id)
            pipe.hmset(key, result_data)

        # チーム勝利数ランキング更新
        pipe.zadd('ranking:team:win', win_team_id, victory_count)

        pipe.execute()

    # 相手ユーザーに対する勝敗情報を登録
    def regist_user_win_or_lose(self, war_id, team_id, user_id, enemy_user_id, war_result):

        def get_datetime_from_serial():
            now_time = get_serial_date()
            base = datetime.strptime('1970-01-01 00:00:00', '%Y-%m-%d %H:%M:%S')
            return (base + timedelta(0, now_time)).strftime('%Y-%m-%d %H:%M:%S')

        pipe = self._redis.pipeline()
        key = 'war:%s:detail' % war_id
        pipe.sadd(key, '%s,%s,%s,%s,%s' % (team_id, user_id, enemy_user_id, war_result, get_datetime_from_serial()))
        pipe.expire(key, options.redis_war_data_expire)
        pipe.execute()

    # 抗争に参戦する
    def enter_war(self, war_id, team_id, user_id, now_time, expire_time):

        key = '{0}:'.format(war_id)
        sha = '7ca21fb843cfg97dc4e2f52c09a90383b18ed087'
        lua_file_name = 'WarEnter.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        return msgpack.unpackb(self._redis.evalsha(sha, 1, key, team_id, user_id, now_time, expire_time))

    # 抗争から退出する
    def exit_war(self, war_id, user_id, team_id, expire_time):

        key = '{0}:'.format(war_id)
        sha = '06465febddfg32d5baa37c481e1d76cdbfa697635'
        lua_file_name = 'WarExit.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        return msgpack.unpackb(self._redis.evalsha(sha, 1, key, user_id, team_id, expire_time))

    # タイムアップ時の勝敗を決定する
    def timeup_judge_win_team(self, war_id, team_id, enemy_team_id, expire_time, result_code):

        key = '{0}:'.format(war_id)
        sha = 'c64e00ert706df7e51da5521d4bde31e80ddbeb60'
        lua_file_name = 'WarTimeupJudgeWinTeam.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        return msgpack.unpackb(self._redis.evalsha(sha, 1, key, team_id, enemy_team_id, expire_time, result_code))

    # 抗争終了カウントダウンチェック
    def war_get_end_countdown(self, war_id):

        key = '{0}:'.format(war_id)
        sha = 'kkkkkac706df7e51da5521d4bde31e80ddbeb60'
        lua_file_name = 'WarGetEndCountdown.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        return msgpack.unpackb(self._redis.evalsha(sha, 1, key, get_serial_date()))

    # 抗争終了カウントダウンチェック
    def war_end_countdown(self, war_id):

        key = '{0}:'.format(war_id)
        sha = 'pppppac706df7e51da5521d4bde31e80ddbeb60'
        lua_file_name = 'WarEndCountdown.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        return msgpack.unpackb(self._redis.evalsha(sha, 1, key))

    # 抗争結果登録完了
    def finish(self, war_id, expire_time):

        key = '{0}:is_end'.format(war_id)
        sha = 'ce13dfadb93ghf3130e569a14838397a8a4ed893'
        lua_file_name = 'WarFinish.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        self._redis.evalsha(sha, 1, key, expire_time)

    # 敵情報詳細取得(初回アクセス時のみ)
    def get_enemy_data(self, war_id, team_id, now_time):

        key = '{0}:'.format(war_id)
        sha = 'pplf8ec7accc9fgb8e047478b553d37ba7db4b9fe'
        lua_file_name = 'EnemyGet.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        return msgpack.unpackb(self._redis.evalsha(sha, 1, key, team_id, now_time))

    # 相手選択
    def select_enemy(self, war_id, team_id, user_id, user_name, enemy_user_id, now_time, expire_time):

        key = '{0}:'.format(war_id)
        sha = '867dafd3b3977df441783f258c322e0616c2835b'
        lua_file_name = 'EnemySelect.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        response = msgpack.unpackb(self._redis.evalsha(sha, 1, key, team_id, user_id, user_name, enemy_user_id, now_time, expire_time))
        if response['status'] != 'ok':
            return response

        # アクセス順にデータをソート
        id_list = []
        after_enemy_list = response['after_enemy']['have_enemy_ids']
        for enemy in sorted(after_enemy_list, key=lambda x:int(x['target_lock_time']), reverse=True):
            id_list.append(int(enemy['user_id']))
        response['after_enemy']['have_enemy_ids'] = id_list

        # アクセス順にデータをソート
        id_list = []
        before_enemy_list = response['before_enemy']['have_enemy_ids']
        for enemy in sorted(before_enemy_list, key=lambda x:int(x['target_lock_time']), reverse=True):
            id_list.append(int(enemy['user_id']))
        response['before_enemy']['have_enemy_ids'] = id_list

        return response


    # 抗争終了時の参戦メンバー一覧を取得する
    def get_end_member(self, war_id, win_team_id, lose_team_id):

        key = '{0}:client:'.format(war_id)
        sha = '662caa558cd6cdhf01aa9105e69f6384c92739d8'
        lua_file_name = 'GetEndMember.lua'

        sha = self._load_lua_script(lua_file_name, sha)

        return msgpack.unpackb(self._redis.evalsha(sha, 1, key, win_team_id, lose_team_id))

