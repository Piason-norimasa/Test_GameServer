#!/usr/bin/env python
# -*- coding: utf-8 -*-

from enum import Enum, IntEnum

# 全員死亡から決着までのカウントダウン時間
END_COUNTDOWN_TIME = 30

class ItemCategory(IntEnum):
    zeni = 1
    waru_g = 2
    consumption_item = 3
    custom_ticket = 4
    avatar = 5
    bike = 6
    present_avatar = 7
    present_bike = 8
    sticker = 9
    gold = 10
    satutaba = 11
    gacha_ticket = 12
    other_item = 13
    event_item = 999

class ZeniHistory(IntEnum):
    avatar_buy = 1
    bike_buy = 2
    donate = 3
    create_team = 4
    war = 5
    battle = 6
    present = 7
    repair = 8
    regist = 9
    maintenance = 10
    custom = 11
    barricade_buy = 12
    gacha = 13
    evolve = 14
    compose = 15

class WaruGHistory(IntEnum):
    avatar_buy = 1
    bike_buy = 2
    item_buy = 3
    ticket_buy = 4
    atm = 5
    custom = 6
    present = 7
    maintenance = 8
    gacha_ticket_buy = 9
    other_item_buy = 10
    nitro_buy = 11
    barricade_buy = 12
    caliper_buy = 13
    tower_continue = 14
    war = 15
    gacha = 16
    change_dir = 17
    fuel_buy = 18
    fuel_stock_buy = 19

class TeamActivityCategory(IntEnum):
    create = 1
    enlistment = 2
    secession = 3
    fire = 4
    donate = 5
    war_win = 6
    war_lose = 7
    war_even = 8
    get_child = 9
    fire_child = 10
    fire_parent = 11
    parent_away = 12
    child_away = 13
    raid_win = 14
    raid_lose = 15
    set_activity_time = 16
    set_play_style = 17
    set_criteria = 18
    change_name = 19
    takeover_leader = 20
    appointment_sub_leader = 21

class TeamPosition(IntEnum):
    leader = 0
    sub_leader = 1

class ActionType(IntEnum):
    unknown = -1
    normal_attack = 0
    skill_attack = 10
    use_item_hp_heal = 20
    use_item_dead_heal = 21
    use_item_skill_heal = 22

class BattleSkillType(IntEnum):
    unknown = 0
    straight_punch = 1
    counter = 2
    charge = 3

class ConsumptionItem(IntEnum):
    small = 0
    big = 1
    brave = 2
    gasoline = 3
    aed = 4
    skill = 5
    small_private = 100
    big_private = 101
    brave_private = 102
    gasoline_private = 103
    aed_private = 104
    skill_private = 105

