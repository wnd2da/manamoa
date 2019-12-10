# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
import logging
import threading
import Queue
import json
# third-party

# sjva 공용
from framework import db, scheduler, path_data
from framework.job import Job
from framework.util import Util
from framework.logger import get_logger

# 패키지
import system
from .model import ModelSetting
from logic_manamoa import LogicMD

package_name = __name__.split('.')[0].split('_sjva')[0]
logger = get_logger(package_name)
#########################################################

class QueueEntity:
    static_index = 0
    entity_list = []

    def __init__(self):
        self.type = None
        self.manga_id = None
        self.wr_id = None
        #self.all_download = False
        self.episodes = []
        self.index = QueueEntity.static_index
        self.title = None
        self.status = '대기'
        QueueEntity.static_index += 1
        QueueEntity.entity_list.append(self)
        self.auto = False

    def as_dict(self):
        d = {
            'index' : self.index,
            'manga_id' : self.manga_id,
            'wr_id' : self.wr_id,
            'episodes' : [x.as_dict() for x in self.episodes],
            'title' : self.title, 
            'status' : self.status,
            'auto' : self.auto
        }
        return d

    def toJSON(self):
        #return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True, indent=4)
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)


    @staticmethod
    def create(t, manga_id, wr_id, auto, title):
        if wr_id is not None:
            for e in QueueEntity.entity_list:
                if e.wr_id == wr_id:
                    return
            ret = QueueEntity()
            ret.wr_id = wr_id
            ret.type = t
            ret.auto = auto
            ret.title = title
            return ret
        else:
            for e in QueueEntity.entity_list:
                if e.manga_id == manga_id:
                    return
            ret = QueueEntity()
            ret.manga_id = manga_id
            ret.type = t
            ret.auto = auto
            ret.title = title
            return ret

    def add(self, wr_id):
        e = QueueEntityEpisode()
        e.wr_id = wr_id
        e.manga_id = self.manga_id
        e.index = len(self.episodes)
        e.queue_index = self.index
        self.episodes.append(e)




class QueueEntityEpisode:
    def __init__(self):
        self.index = -1
        self.wr_id = None
        self.status = "대기"
        self.title = None
        self.current_image_index = 0
        self.total_image_count = 0
        self.maintitle = None
        self.queue_index = -1
        self.manga_id = None
    
    def as_dict(self):
        d = {
            'index' : self.index,
            'wr_id' : self.wr_id,
            'status' : self.status,
            'title' : self.title,
            'current_image_index' : self.current_image_index, 
            'total_image_count' : self.total_image_count, 
            'maintitle' : self.maintitle, 
            'queue_index' : self.queue_index, 
            'manga_id' : self.manga_id, 
        }
        return d

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, sort_keys=True)



class LogicQueue(object):
    download_queue = None
    download_thread = None
    entity_list = []

    @staticmethod
    def queue_start():
        try:
            if LogicQueue.download_queue is None:
                LogicQueue.download_queue = Queue.Queue()
            
            if LogicQueue.download_thread is None:
                LogicQueue.download_thread = threading.Thread(target=LogicQueue.download_thread_function, args=())
                LogicQueue.download_thread.daemon = True  
                LogicQueue.download_thread.start()
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
    def download_thread_function():
        while True:
            try:
                entity = LogicQueue.download_queue.get()
                logger.debug('Queue receive item:%s %s', entity.manga_id, entity.wr_id)
                LogicMD.download(entity)
                LogicQueue.download_queue.task_done()    
            except Exception as e: 
                logger.error('Exception:%s', e)
                logger.error(traceback.format_exc())

    @staticmethod
    def add_queue_manga(manga_id, auto, title):
        try:
            entity = QueueEntity.create('all', manga_id, None, auto, title)
            if entity is not None:
                LogicQueue.download_queue.put(entity)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    @staticmethod
    def add_queue_episode(manga_id, wr_id, auto, title):
        try:
            entity = QueueEntity.create('episode', manga_id, wr_id, auto, title)
            if entity is not None:
                LogicQueue.download_queue.put(entity)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
    
    @staticmethod
    def completed_remove():
        try:
            new_list = []
            for e in QueueEntity.entity_list:
                if e.status not in ['완료', '제외']:
                    new_list.append(e)
            QueueEntity.entity_list = new_list
            import plugin
            plugin.send_queue_list()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def reset_queue():
        try:

            with LogicQueue.download_queue.mutex:
                LogicQueue.download_queue.queue.clear()
            QueueEntity.entity_list = []
            import plugin
            plugin.send_queue_list()
            LogicMD.stop()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

            
