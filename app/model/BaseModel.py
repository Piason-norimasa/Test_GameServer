#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tornado.options
from tornado.options import define, options

import MySQLdb

class BaseModel(object):

    # TODO: 一旦残しておく
    DB_TYPE_MASTER  = 'master'
    DB_TYPE_SLAVE   = 'slave'
    DB_TYPE_LOG     = 'log'

    _db             = None

    def __init__(self, db):

        self._db = db