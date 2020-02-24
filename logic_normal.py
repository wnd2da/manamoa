# -*- coding: utf-8 -*-
#########################################################
# python
import os
import sys
import traceback
import logging
import threading
import Queue
# third-party
from selenium.webdriver.support.ui import WebDriverWait

# sjva 공용
from framework import db, scheduler, path_data
from framework.job import Job
from framework.util import Util
from framework.logger import get_logger

# 패키지
import system
from .plugin import package_name, logger
from .model import ModelSetting, ModelManamoaItem


#########################################################
import urllib
import time
import json
import re
from datetime import datetime
import shutil
import zipfile

try:
    import requests
    from bs4 import BeautifulSoup
    import cfscrape
    from discord_webhook import DiscordWebhook
    from google_drive_downloader import GoogleDriveDownloader as gdd
    from PIL import Image
except:
    requirements = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')
    if os.system('python -m pip install -r %s' % (requirements)) != 0:
        os.system('wget https://bootstrap.pypa.io/get-pip.py')
        os.system('python get-pip.py' % python)
        os.system('python -m pip install -r %s' % (requirements))

import requests
from bs4 import BeautifulSoup
from sqlitedict import SqliteDict
import cfscrape
from PIL import Image
#############################################################################################

class LogicNormal(object):
    scraper = None
    stop_flag = False
    driver = None

    @staticmethod
    def scheduler_function():
        from logic_queue import LogicQueue
        logger.debug('LogicNormal Start')
        try:
            LogicNormal.stop_flag = False
            url = '%s/bbs/board.php?bo_table=manga' % ModelSetting.get('sitecheck')
            page_source = LogicNormal.pageparser(url)
            soup = BeautifulSoup(page_source, 'html.parser')
            for t in soup.find_all('div', class_='post-row'):
                a_tags = t.find_all('a')
                manga_id = a_tags[1]['href'].split('manga_id=')[1]
                title = a_tags[2].text.strip().replace('NEW ', '')
                if ModelSetting.get('all_download') == 'True':
                    LogicQueue.add_queue_manga(manga_id, True, title)
                else:
                    wr_id = a_tags[0]['href'].split('wr_id=')[1]
                    LogicQueue.add_queue_episode(manga_id, wr_id, True, title)
                if LogicNormal.stop_flag:
                    break
            import plugin
            plugin.send_queue_list()
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    @staticmethod
    def titlereplace(title):
        return re.sub('[\\/:*?\"<>|]', '', title).strip()


    @staticmethod
    def image_download(url, image_filepath, decoder):
        try:
            headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"}
            image_data = requests.get(url,headers=headers,stream=True)
            if decoder is None:
                with open(image_filepath, 'wb') as handler:
                    handler.write(image_data.content)
            else:
                from PIL import Image
                im = Image.open(image_data.raw)
                output = decoder.decode(im)
                output.save(image_filepath)
            return image_data.status_code
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    # 압축할 폴더 경로를 인자로 받음. 폴더명.zip 생성
    @staticmethod
    def makezip(zip_path):
        try:
            if os.path.isdir(zip_path):
                zipfilename = os.path.join(os.path.dirname(zip_path), '%s.zip' % os.path.basename(zip_path))
                fantasy_zip = zipfile.ZipFile(zipfilename, 'w')
                for f in os.listdir(zip_path):
                    if f.endswith('.jpg') or f.endswith('.png'):
                        src = os.path.join(zip_path, f)
                        fantasy_zip.write(src, os.path.basename(src), compress_type = zipfile.ZIP_DEFLATED)
                fantasy_zip.close()
            shutil.rmtree(zip_path)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())



    @staticmethod
    def pageparser(url):
        try:
            #if ModelSetting.get('use_selenium') == 'True':
            from system import SystemLogicSelenium
            return SystemLogicSelenium.get_pagesoruce_by_selenium(url, '//footer[@class="at-footer"]')
            
            headers = {"user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"}
            if ModelSetting.get('proxy') == 'False' and ModelSetting.get('cloudflare_bypass') == 'False':
                page_source = requests.get(url,headers=headers).text
            elif ModelSetting.get('proxy') == 'True' and ModelSetting.get('cloudflare_bypass') == 'False':
                page_source = requests.get(url,headers=headers,proxies={"https": ModelSetting.get('proxy_url'), 'http':ModelSetting.get('proxy_url')}).text
            elif ModelSetting.get('proxy') == 'False' and ModelSetting.get('cloudflare_bypass') == 'True':
                if LogicNormal.scraper is None:
                    LogicNormal.scraper = cfscrape.create_scraper()
                page_source = LogicNormal.scraper.get(url,headers=headers).text
            elif ModelSetting.get('proxy') == 'True' and ModelSetting.get('cloudflare_bypass') == 'True':
                if LogicNormal.scraper is None:
                    LogicNormal.scraper = cfscrape.create_scraper()
                page_source = LogicNormal.scraper.get(url,headers=headers,proxies={"https": ModelSetting.get('proxy_url'), 'http':ModelSetting.get('proxy_url') }).text
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None
        return page_source

    # 큐에서 호출
    @staticmethod
    def download(entity):
        import plugin
        from .logic_queue import QueueEntityEpisode
        LogicNormal.stop_flag = False
        try:
            if entity.auto:
                flag = LogicNormal.is_exist_download_list(entity.title)
            else:
                flag = True

            if flag:
                if entity.wr_id is None:
                    LogicNormal.make_episode_list_from_manga_id(entity)
                    plugin.socketio_callback('queue_one', entity.as_dict(), encoding=False)
                else:
                    entity.add(entity.wr_id)
                    plugin.socketio_callback('queue_one', entity.as_dict(), encoding=False)
                for e in entity.episodes:
                    m = ModelManamoaItem.get(e.wr_id)
                    if m is None:
                        if LogicNormal.episode_download(e):
                            ModelManamoaItem.save(e)
                    else:
                        e.title = m.title
                        e.status = '이미 받음'
                        plugin.socketio_callback('episode', e.as_dict(), encoding=False)
                    if LogicNormal.stop_flag:
                        break
                entity.status = '완료'
                plugin.socketio_callback('queue_one', entity.as_dict(), encoding=False)
            else:
                entity.status = '제외'
                plugin.socketio_callback('queue_one', entity.as_dict(), encoding=False)
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
            return None

    @staticmethod
    def stop():
        LogicNormal.stop_flag = True

    @staticmethod
    def make_episode_list_from_manga_id(manga):
        try:
            url = ModelSetting.get('sitecheck') + '/bbs/page.php?hid=manga_detail&manga_id=' + manga.manga_id
            page_source = LogicNormal.pageparser(url)
            soup = BeautifulSoup(page_source, 'html.parser')
            manga.title = LogicNormal.titlereplace(soup.find('div', class_='red title').text)
            for t in list(reversed(soup.find_all('div', class_='slot'))):
                manga.add(t.find('a')['href'].split('wr_id=')[1])
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())


    # 에피소드 한편을 다운로드 한다.  wr_id= 포함된 url, 저장경로
    @staticmethod
    def episode_download(queue_entity_episode):
        import plugin
        wr_id = queue_entity_episode.wr_id
        logger.debug('Episode Download wr_id:%s', wr_id)
        try:
            from system import SystemLogicSelenium
            if LogicNormal.driver is None:
                LogicNormal.driver = SystemLogicSelenium.create_driver()

            driver = LogicNormal.driver
            url = '%s/bbs/board.php?bo_table=manga&wr_id=%s' % (ModelSetting.get('sitecheck'), wr_id)
            driver.get(url)
            
            fix_tag = WebDriverWait(driver, 30).until(lambda driver: driver.find_element_by_xpath('//*[@id="thema_wrapper"]/div[3]/div/div/div[1]/div[2]/div[3]/div'))
            SystemLogicSelenium.remove_element(driver, fix_tag)


            tag = WebDriverWait(driver, 30).until(lambda driver: driver.find_element_by_xpath('//*[@id="thema_wrapper"]/div[3]/div/div/div[1]/div[2]/div[1]/div/div[1]/a[2]'))


            queue_entity_episode.manga_id = tag.get_attribute('href').split('=')[-1]
            title = driver.title
            queue_entity_episode.title = LogicNormal.titlereplace(title)
            match = re.compile(ur'(?P<main>.*?)((단행본.*?)?|특별편)?(\s(?P<sub>(\d|\-|\.)*?(화|권)))?(\-)?(전|후|중)?(\s?\d+(\-\d+)?화)?(\s\(완결\))?\s?$').match(title)
            
            if match:
                queue_entity_episode.maintitle = match.group('main').strip()
            else:
                match2 = re.compile(ur'(?P<main>.*?)\s시즌')
                if match2:
                    queue_entity_episode.maintitle = match2.group('main').strip()
                else:
                    queue_entity_episode.maintitle = title
                    logger.debug('not match')
            queue_entity_episode.maintitle = LogicNormal.titlereplace(queue_entity_episode.maintitle)

            if ModelSetting.get('use_title_folder') == 'True':
                download_path = os.path.join(ModelSetting.get('dfolder'), queue_entity_episode.maintitle, queue_entity_episode.title)
            else:
                download_path = os.path.join(ModelSetting.get('dfolder'), queue_entity_episode.title)
           

            logger.debug(title)
            logger.debug(queue_entity_episode.maintitle)

            image_tags = WebDriverWait(driver, 30).until(lambda driver: driver.find_elements_by_xpath('//*[@id="thema_wrapper"]/div[3]/div/div/div[1]/div[2]/div[5]/div/img'))

            
            queue_entity_episode.total_image_count = len(image_tags)
            if not os.path.exists(download_path):
                os.makedirs(download_path)
            queue_entity_episode.status = '캡처중'
            plugin.socketio_callback('episode', queue_entity_episode.as_dict(), encoding=False)
            
            full = SystemLogicSelenium.full_screenshot(driver)
            if full is None:
                queue_entity_episode.status = '실패'
                plugin.socketio_callback('episode', queue_entity_episode.as_dict(), encoding=False)    
            else:
                queue_entity_episode.status = '파일 생성중'
                for idx, tag in enumerate(image_tags):
                    image_filepath = os.path.join(download_path, str(idx+1).zfill(5)+'.png')
                    left = tag.location['x'] 
                    top = tag.location['y'] 
                    right = tag.location['x'] + tag.size['width']
                    bottom = top + tag.size['height'] 

                    logger.debug('%s %s %s %s %s', idx, left, top, right, bottom)

                    im = full.crop((left, top, right, bottom)) # defines crop points
                    im.save(image_filepath)
                    
                    queue_entity_episode.current_image_index = idx
                    plugin.socketio_callback('episode', queue_entity_episode.as_dict(), encoding=False)

                    
                if ModelSetting.get('zip') == 'True':
                    LogicNormal.makezip(download_path)
                queue_entity_episode.status = '완료'
                plugin.socketio_callback('episode', queue_entity_episode.as_dict(), encoding=False)
                return True
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())

    # 다운여부 판단
    @staticmethod
    def is_exist_download_list(title):
        try:
            flag = False
            tmp = ModelSetting.get('downlist').strip()
            if tmp == '':
                flag = True
            downlist = tmp.split('|')
            title = LogicNormal.titlereplace(title).replace(' ', '')
            for downcheck in downlist:
                downcheck = downcheck.strip()
                if downcheck == '':
                    pass
                else:
                    if title.find(LogicNormal.titlereplace(downcheck).replace(' ', '')) != -1:
                        flag = True
                        break
            tmp = ModelSetting.get('blacklist').strip()
            if tmp == '':
                pass
            else:
                blacklist = tmp.split('|')
                for downcheck in blacklist:
                    downcheck = downcheck.strip()
                    if downcheck == '':
                        pass
                    else:
                        if title.find(LogicNormal.titlereplace(downcheck).replace(' ', '')) != -1:
                            flag = False
                            break
        except Exception as e:
            logger.error('Exception:%s', e)
            logger.error(traceback.format_exc())
        return flag
