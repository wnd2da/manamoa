# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
import logging
import threading
import time
# third-party
from sqlalchemy import desc

# sjva 공용
from framework import db, scheduler, path_data
from framework.job import Job
from framework.util import Util
from framework.logger import get_logger

# 패키지
from .plugin import package_name, logger
from .model import ModelSetting, ModelManamoaItem
from .logic_queue import LogicQueue

#########################################################


class Logic(object):
    db_default = {
        'auto_start' : 'False',
        'interval' : '30',
        'web_page_size' : '30',
        "sitecheck" : "https://manamoa17.net",
        "all_download" : "False",
        "zip" : "True",
        "cloudflare_bypass" : "False",
        "proxy" : "False",
        "proxy_url" : "",
        "downlist" : "",
        "discord_webhook" : "False",
        "discord_webhook_url" : "",
        'dfolder' : os.path.join(path_data, 'manamoa'),
        "pagecount" : "1",
        "use_selenium" : 'False',
        "blacklist" : "",
        'use_title_folder' : 'True', 
        'server_number' : '17'
    }


    @staticmethod
    def db_init():
        try:
            for key, value in Logic.db_default.items():
                if db.session.query(ModelSetting).filter_by(key=key).count() == 0:
                    db.session.add(ModelSetting(key, value))
            db.session.commit()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def plugin_load():
        try:
            logger.debug('%s plugin_load', package_name)
            # DB 초기화
            Logic.db_init()

            # 필요 패키지 설치
            try:
                from bs4 import BeautifulSoup
                import cfscrape
                from discord_webhook import DiscordWebhook
            except:
                try:
                    os.system('pip install -r %s' % os.path.join(os.path.dirname(__file__), 'requirements.txt'))
                except:
                    logger.error('pip install error!!')
                    pass

            # 다운로드 폴더 생성
            download_path = Logic.get_setting_value('dfolder')
            if not os.path.exists(download_path):
                try:
                    os.mkdir(download_path)
                except:
                    logger.error('donwload_path make error!!')
            # 편의를 위해 json 파일 생성
            from plugin import plugin_info
            Util.save_from_dict_to_json(plugin_info, os.path.join(os.path.dirname(__file__), 'info.json'))

            LogicQueue.queue_start()

            # 자동시작 옵션이 있으면 보통 여기서
            if ModelSetting.query.filter_by(key='auto_start').first().value == 'True':
                Logic.scheduler_start()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def plugin_unload():
        try:
            logger.debug('%s plugin_unload', package_name)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def scheduler_start():
        try:
            logger.debug('%s scheduler_start', package_name)
            interval = Logic.get_setting_value('interval')
            job = Job(package_name, package_name, interval, Logic.scheduler_function, u"마나모아 다운로더", False)
            scheduler.add_job_instance(job)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def scheduler_stop():
        try:
            logger.debug('%s scheduler_stop', package_name)
            scheduler.remove_job(package_name)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def setting_save(req):
        try:
            for key, value in req.form.items():
                logger.debug('Key:%s Value:%s', key, value)
                entity = db.session.query(ModelSetting).filter_by(key=key).with_for_update().first()
                entity.value = value
            db.session.commit()
            return True
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            logger.error('key:%s value:%s', key, value)
            return False


    @staticmethod
    def get_setting_value(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def scheduler_function():
        try:
            from logic_manamoa import LogicMD
            LogicMD.start()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    job_thread = None
    @staticmethod
    def one_execute():
        try:
            if scheduler.is_include(package_name):
                if scheduler.is_running(package_name):
                    ret = 'is_running'
                else:
                    scheduler.execute_job(package_name)
                    ret = 'scheduler'
            else:
                def func():
                    time.sleep(2)
                    Logic.scheduler_function()
                    Logic.job_thread = None
                if Logic.job_thread is None:
                    Logic.job_thread = threading.Thread(target=func, args=())
                    Logic.job_thread.start()
                    ret = 'thread'
                else:
                    ret = 'is_running'
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            ret = 'fail'
        return ret


    @staticmethod
    def reset_db():
        try:
            db.session.query(ModelManamoaItem).delete()
            db.session.commit()
            return True
        except Exception as e: 
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    # 기본 구조 End
    ##################################################################

    @staticmethod
    def download_by_request(req):
        try:
            manga_id = req.form['manga_id']
            manga_id = None if manga_id == '' else manga_id
            wr_id = req.form['wr_id']
            from logic_queue import LogicQueue
            if manga_id is not None:
                LogicQueue.add_queue_manga(manga_id, False, None)
            else:
                LogicQueue.add_queue_episode(None, wr_id, False, None)
            return True
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def get_zip_list():
        try:
            ret = []
            download_path = Logic.get_setting_value('dfolder')
            tmp = os.listdir(download_path)
            for t in tmp:
                title_path = os.path.join(download_path, t)
                if os.path.isdir(title_path):
                    zip_list = os.listdir(title_path)
                    for z in zip_list:
                        zip_path = os.path.join(title_path, z)
                        if os.path.isfile(zip_path) and zip_path.endswith('.zip'):
                            ret.append('dp/%s/%s' % (t, z))
            #return '|'.join(ret)
            return ret

        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def item_list(req):
        try:
            ret = {}
            page = 1
            page_size = 30
            job_id = ''
            search = ''
            if 'page' in req.form:
                page = int(req.form['page'])
            if 'search_word' in req.form:
                search = req.form['search_word']
            query = db.session.query(ModelManamoaItem)
            if search != '':
                query = query.filter(ModelManamoaItem.title.like('%'+search+'%'))
            query = query.order_by(desc(ModelManamoaItem.id))
            count = query.count()
            query = query.limit(page_size).offset((page-1)*page_size)
            lists = query.all()
            ret['list'] = [item.as_dict() for item in lists]
            ret['paging'] = Util.get_paging_info(count, page, page_size)
            return ret
        except Exception, e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def list_remove(req):
        try:
            db_id = int(req.form['id'])
            item = db.session.query(ModelManamoaItem).filter(ModelManamoaItem.id == db_id).first()
            
            if item is not None:
                db.session.delete(item)
                db.session.commit()
            return True
        except Exception, e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def list_all_download(req):
        try:
            db_id = int(req.form['id'])
            item = db.session.query(ModelManamoaItem).filter(ModelManamoaItem.id == db_id).first()
            if item is not None:
                LogicQueue.add_queue_manga(item.manga_id, False, None)
                return True
            return False
        except Exception, e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False

    @staticmethod
    def list_add_blacklist(req):
        try:
            db_id = int(req.form['id'])
            item = db.session.query(ModelManamoaItem).filter(ModelManamoaItem.id == db_id).first()
            if item is not None:
                from logic_manamoa import LogicMD
                tmp = LogicMD.titlereplace(item.main_title)
                entity = db.session.query(ModelSetting).filter_by(key='blacklist').with_for_update().first()
                if entity.value.strip() == '':
                    entity.value = tmp
                else:
                    entity.value = entity.value + '|' + tmp
                db.session.commit()
                return True
            return False
        except Exception, e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return False


