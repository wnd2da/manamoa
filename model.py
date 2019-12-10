# -*- coding: utf-8 -*-
#########################################################
# python
import os
import traceback
import json
from datetime import datetime

# third-party

# sjva 공용
from framework.logger import get_logger
from framework import db, app, path_app_root
# 패키지

# 로그
package_name = __name__.split('.')[0].split('_sjva')[0]
logger = get_logger(package_name)

if app.config['config']['run_by_real']:
    db_file = os.path.join(path_app_root, 'data', 'db', '%s.db' % package_name)
    app.config['SQLALCHEMY_BINDS'][package_name] = 'sqlite:///%s' % (db_file)


class ModelSetting(db.Model):
    __tablename__ = 'plugin_%s_setting' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.String, nullable=False)
 
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __repr__(self):
        return repr(self.as_dict())

    def as_dict(self):
        return {x.name: getattr(self, x.name) for x in self.__table__.columns}

    @staticmethod
    def get(key):
        try:
            return db.session.query(ModelSetting).filter_by(key=key).first().value
        except Exception as e:
            logger.error('Exception:%s %s', e, key)
            logger.error(traceback.format_exc())

#########################################################

"""
class ModelManamoaManga(db.Model):
    __tablename__ = 'plugin_%s_manga' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    json = db.Column(db.JSON)
    created_time = db.Column(db.DateTime)

    manga_id = db.Column(db.Integer)
    manga_title = db.Column(db.String)
    recommend = db.Column(db.Integer)
    genre = db.Column(db.String)
    period = db.Column(db.String)
    author = db.Column(db.String)
    update_time = db.Column(db.DateTime)

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S') 
        ret['update_time'] = self.update_time.strftime('%m-%d %H:%M:%S') if self.update_time is not None else ''
        return ret


class ModelManamoaEpisode(db.Model):
    __tablename__ = 'plugin_%s_episode' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    json = db.Column(db.JSON)
    created_time = db.Column(db.DateTime)

    wr_id = db.Column(db.Integer)
    episode_title = db.Column(db.String)
    score = db.Column(db.Integer)
    manga_id = db.Column(db.Integer, db.ForeignKey('plugin_%s_manga.id' % package_name))
    manga = db.relationship('ModelManamoaManga')

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S') 
        return ret
"""

class ModelManamoaItem(db.Model):
    __tablename__ = 'plugin_%s_item' % package_name
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = package_name

    id = db.Column(db.Integer, primary_key=True)
    json = db.Column(db.JSON)
    created_time = db.Column(db.DateTime)

    manga_id = db.Column(db.String)
    wr_id = db.Column(db.String)
    title = db.Column(db.String)
    main_title = db.Column(db.String)
    total_image_count = db.Column(db.Integer)

    def __init__(self):
        self.created_time = datetime.now()

    def as_dict(self):
        ret = {x.name: getattr(self, x.name) for x in self.__table__.columns}
        ret['created_time'] = self.created_time.strftime('%m-%d %H:%M:%S') 
        return ret
    
    @staticmethod
    def save(entity):
        m = ModelManamoaItem()
        m.manga_id = entity.manga_id
        m.wr_id = entity.wr_id
        m.title = entity.title
        m.total_image_count = entity.total_image_count
        m.main_title = entity.maintitle
        db.session.add(m)
        db.session.commit()

    @staticmethod
    def get(wr_id):
        try:
            return db.session.query(ModelManamoaItem).filter_by(wr_id=wr_id).first()
        except Exception as e:
            logger.error('Exception:%s %s', e, wr_id)
            logger.error(traceback.format_exc())
