#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/app')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/app/model')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/app/logic')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/app/redis')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/app/packet')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/app/web')
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/app/lib')

import tornado.options
from tornado.options import define, options, parse_command_line, parse_config_file
from AppServer import AppServer

# 設定
define('config',                default='',     type=str)
define('web_port',              default=8080,   type=int)
define('ws_port',               default=8080,   type=int)
define('ssl_crtfile',           default='/etc/ssl/test_server.crt',     type=str)
define('ssl_keyfile',           default='/etc/ssl/test_server.key',     type=str)

define('redis_war_data_expire', default=7200,   type=int)
define('redis_socket_host',     default='',     type=str)
define('redis_socket_port',     default=6379,   type=int)
define('redis_socket_db',       default=0,      type=int)
define('redis_app_host',        default='',     type=str)
define('redis_app_port',        default=6379,   type=int)
define('redis_app_db',          default=0,      type=int)

define('db_master_host',        default='',     type=str)
define('db_master_port',        default=3306,   type=int)
define('db_slave_host',         default='',     type=str)
define('db_slave_port',         default=3306,   type=int)
define('db_log_host',           default='',     type=str)
define('db_log_port',           default=3306,   type=int)
define('db_user',               default='',     type=str)
define('db_pass',               default='',     type=str)
define('db_name',               default='',     type=str)
define('db_log_name',           default='',     type=str)

# ログ設定
options.logging = 'info'
options.log_to_stderr = None
options.log_file_prefix = '/var/www/bakuden/logs/app.log'
options.log_file_max_size = 100 * 1000 * 1000
options.log_file_num_backups = 10

# confg/development.cfg (環境設定ファイル)をロード
parse_command_line(final=False)
parse_config_file('/var/www/bakuden/config/%s.cfg' % options.config)

def main():

    logging.info('[app-server start]--------------------------------------------------------------------------------------------------------------------')

    try:

        # サーバー起動
        app = AppServer()
        app.start_server()

    except Exception as e:

        # サーバーアプリケーションエラー
        import traceback
        logging.error(e.message)
        logging.error(traceback.format_exc())

    logging.info('[app-server stop]--------------------------------------------------------------------------------------------------------------------')

if __name__ == '__main__':  
    main()
