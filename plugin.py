# -*- coding: utf-8 -*-
#########################################################
# 고정영역
#########################################################
# python
import os
import sys
import traceback
import json

# third-party
from flask import Blueprint, request, Response, render_template, redirect, jsonify, url_for, send_from_directory
from flask_login import login_required
from flask_socketio import SocketIO, emit, send

# sjva 공용
from framework.logger import get_logger
from framework import app, db, scheduler, socketio, path_app_root
from framework.util import Util, AlchemyEncoder
from system.logic import SystemLogic
            
# 패키지
package_name = __name__.split('.')[0]
logger = get_logger(package_name)

from .logic import Logic
from .model import ModelSetting


blueprint = Blueprint(package_name, package_name, url_prefix='/%s' %  package_name, template_folder=os.path.join(os.path.dirname(__file__), 'templates'), static_folder=os.path.join(os.path.dirname(__file__), 'kthoom'), static_url_path='kthoom')

def plugin_load():
    Logic.plugin_load()

def plugin_unload():
    Logic.plugin_unload()

plugin_info = {
    'version' : '0.2.1',
    'name' : '마나모아 다운로드',
    'category_name' : 'service',
    'icon' : '',
    'developer' : 'soju6jan',
    'description' : '마나모아 다운로드<br>원작자 :noname님',
    'home' : 'https://github.com/soju6jan/manamoa',
    'more' : '',
}
#########################################################

# 메뉴 구성.
menu = {
    'main' : [package_name, '마나모아 다운로드'],
    'sub' : [
        ['setting', '설정'], ['request', '요청'], ['queue', '큐'], ['list', '목록'], ['log', '로그']
    ], 
    'category' : 'service',
}  

#########################################################
# WEB Menu
#########################################################
@blueprint.route('/')
def home():
    return redirect('/%s/setting' % package_name)
    
@blueprint.route('/<sub>')
@login_required
def first_menu(sub): 
    arg = ModelSetting.to_dict()
    arg['package_name']  = package_name
    if sub == 'setting':
        arg['scheduler'] = str(scheduler.is_include(package_name))
        arg['is_running'] = str(scheduler.is_running(package_name))
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub == 'request':
        arg['is_running'] = str(scheduler.is_running(package_name))
        return render_template('%s_%s.html' % (package_name, sub), arg=arg)
    elif sub in ['queue', 'list']:
        return render_template('%s_%s.html' % (package_name, sub))
    elif sub == 'log':
        return render_template('log.html', package=package_name)
    return render_template('sample.html', title='%s - %s' % (package_name, sub))

#########################################################
# For UI (보통 웹에서 요청하는 정보에 대한 결과를 리턴한다.)
#########################################################
@blueprint.route('/ajax/<sub>', methods=['GET', 'POST'])
def ajax(sub):
    logger.debug('AJAX %s %s', package_name, sub)
    try:
        if sub == 'setting_save':
            ret = ModelSetting.setting_save(request)
            return jsonify(ret)
        elif sub == 'scheduler':
            go = request.form['scheduler']
            logger.debug('scheduler :%s', go)
            if go == 'true':
                Logic.scheduler_start()
            else:
                Logic.scheduler_stop()
            return jsonify(go)
        elif sub == 'one_execute':
            ret = Logic.one_execute()
            return jsonify(ret)
        elif sub == 'reset_db':
            ret = Logic.reset_db()
            return jsonify(ret)



  
        
        elif sub == 'download_by_request':
            try:
                ret = Logic.download_by_request(request)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'completed_remove':
            try:
                from logic_queue import LogicQueue
                ret = LogicQueue.completed_remove()
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'reset_queue':
            try:
                from logic_queue import LogicQueue
                ret = LogicQueue.reset_queue()
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'item_list':
            try:
                ret = Logic.item_list(request)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'list_remove':
            try:
                ret = Logic.list_remove(request)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'list_all_download':
            try:
                ret = Logic.list_all_download(request)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
        elif sub == 'list_add_blacklist':
            try:
                ret = Logic.list_add_blacklist(request)
                return jsonify(ret)
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())  
        return jsonify('fail')   

    

#########################################################
# API
#########################################################
@blueprint.route('/api/<sub>', methods=['GET', 'POST'])
def api(sub):
    logger.debug('api %s %s', package_name, sub)
    
#########################################################
# kthroom
#########################################################
@blueprint.route('/code/<path:path>', methods=['GET', 'POST'])
def kthroom(path):
    return blueprint.send_static_file('code/' + path)

@blueprint.route('/images/<path:path>', methods=['GET', 'POST'])
def kthroom_images(path):
    return blueprint.send_static_file('images/' + path)

@blueprint.route('/examples/<path:path>', methods=['GET', 'POST'])
def kthroom_examples(path):
    return blueprint.send_static_file('examples/' + path)

@blueprint.route('/dp/<path:path>', methods=['GET', 'POST'])
def kthroom_dp(path):
    tmp = path.split('/')
    real_path = os.path.join(ModelSetting.get('dfolder'), tmp[0], tmp[1])
    real_path = real_path.replace(path_app_root, '')[1:].replace('\\', '/')
    logger.debug('load:%s', real_path)
    return send_from_directory('', real_path)

#########################################################
# socketio
#########################################################
sid_list = []
@socketio.on('connect', namespace='/%s' % package_name)
def connect():
    try:
        logger.debug('socket_connect')
        sid_list.append(request.sid)
        send_queue_list()
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())


@socketio.on('disconnect', namespace='/%s' % package_name)
def disconnect():
    try:
        sid_list.remove(request.sid)
        logger.debug('socket_disconnect')
    except Exception as e: 
        logger.error('Exception:%s', e)
        logger.error(traceback.format_exc())

def socketio_callback(cmd, data, encoding=True):
    if sid_list:
        if encoding:
            data = json.dumps(data, cls=AlchemyEncoder)
            data = json.loads(data)
        socketio.emit(cmd, data, namespace='/%s' % package_name, broadcast=True)


def send_queue_list():
    from logic_queue import QueueEntity
    tmp = QueueEntity.entity_list
    t = [x.as_dict() for x in tmp]
    socketio_callback('queue_list', t, encoding=False)
