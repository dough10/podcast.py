#!/usr/bin/env python3

import os
import sys
import shutil
import requests
import datetime
import xmltodict
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv, set_key

from lib.question import question
from lib.format_filename import format_filename
from lib.headers import headers
from lib.update_id3 import update_ID3, id3Image, load_saved_image
from lib.logs import Logs
from lib.download import dlWithProgressBar
from lib.podcast_episode_exists import podcast_episode_exists
from lib. is_live_url import is_live_url, is_connected, is_valid_url

logger = Logs().get_logger()

load_dotenv()

file_path = os.path.abspath(__file__)
script_folder = os.path.dirname(file_path)

def subscriptions():
  sub_list:str = os.getenv('subscriptions', '')
  return sub_list.split(',') if sub_list else []

class Podcast:

  def __init__(self, url:str) -> None:
    # check internet
    if not is_connected():
      logger.critical('Error connecting to the internet. Please check network connection and try again')
      sys.exit()
      
    self.__podcast_folder:str = os.getenv('podcast_folder')

    if not os.path.exists(self.__podcast_folder):
      logger.critical(f'Folder {self.__podcast_folder} does not exist. check .env')
      sys.exit()

    self.__xmlURL:str = url.strip()

    if not is_valid_url(self.__xmlURL):
      logger.error(f'Invalid URL address: {self.__xmlURL}')
      sys.exit()

    if not is_live_url(self.__xmlURL):
      logger.error(f'Error connecting to {self.__xmlURL}')
      sys.exit()
      
    time_stamp:str = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

    logger.info(time_stamp)
    logger.info(f'Fetching data from: {self.__xmlURL}')

    res = requests.get(self.__xmlURL, headers=headers)
    if res.status_code != 200:
      logger.critical(f'Error getting XML data. Error code {res.status_code}')
      sys.exit()
    try:
      xml = xmltodict.parse(res.content)
    except Exception as e:
      logger.critical(f'Failed parsing XML: {e}')
      sys.exit()

    self.__title:str = xml['rss']['channel']['title']  # the name of the podcast
    self.__list:list[dict] = xml['rss']['channel']['item']  # list of podcast episodes
    self.__location:str = os.path.join(self.__podcast_folder, format_filename(self.__title))

    try:
      self.__imgURL:str = xml['rss']['channel']['image']['url']
    except TypeError:
      self.__imgURL:str = xml['rss']['channel']['image'][0]['url']
    except KeyError:
      self.__imgURL:str = xml['rss']['channel']['itunes:image']['@href']

    logger.info(f'{self.__title}: {str(self.episodeCount())} episodes')


  def fallback_image(self, file) -> None:
    logger.info('using fallback image')
    if hasattr(self, '__image'):
      id3Image(file, self.__image)
    else:
      self.__image = load_saved_image(self.__coverJPG)
      id3Image(file, self.__image)


  def __fileDL(self, episode, epNum, window) -> None:
    """
    Downloads a podcast episode and sets the ID3 tags for the downloaded file.

    Args:
      episode (dict): The metadata of the episode.
      epNum (int): The episode number.

    Returns:
      None
    """
    stats = podcast_episode_exists(self.__title, episode)

    if stats['path'].startswith('\\') or stats['path'].startswith('/'):
        stats['path'] = stats['path'][1:]

    # reflect download progress on UI
    def prog_update(downloaded, total, start_time):
      pass
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").update("{self.__xmlURL}", {downloaded}, {total}, {start_time}, "{stats["filename"]}")')

    # check if the file exists
    if stats['exists']:
      logger.info(f'Episode {stats["filename"]} already downloaded')
      return
    
    path:str = os.path.join(self.__podcast_folder, stats['path'])
    
    logger.info(f'Downloading - {stats["filename"]}')
    # download the file and update ui with progress
    dlWithProgressBar(stats['url'], path, progress_callback=prog_update)
    # tag file with info
    update_ID3(self.__title, episode, path, epNum, self.fallback_image)


  def __get_cover_art(self) -> None:
    self.__coverJPG:str = os.path.join(self.__location, 'cover.jpg')

    if not os.path.exists(self.__coverJPG):
      logger.info(f'saving cover art {self.__coverJPG}')
      res = requests.get(self.__imgURL, headers=headers)
      if res.status_code == 200:
        img = Image.open(BytesIO(res.content))
      else:
        logger.error("Failed to fetch image:", res.status_code)
        return
      logger.info(f'Image format: {img.format}, Mode: {img.mode}, Size: {img.size}')
      width, height = img.size 
      if width > 1000 or height > 1000:
        img.thumbnail((1000, 1000), Image.LANCZOS)
      img.convert('RGB')
      try:
        img.save(self.__coverJPG, 'JPEG')
      except OSError:
        img.save(self.__coverJPG, 'PNG')
      self.__image = img


  def __mkdir(self) -> None:
    if not os.path.exists(self.__podcast_folder):
      logger.error(f'Error accessing location {self.__podcast_folder}')
      logger.error('Check if network drive is mounted')
      sys.exit()
    if not os.path.exists(self.__location):
      logger.info(f'Creating folder {self.__location}')
      try:
        os.makedirs(self.__location)
      except OSError as e:
        raise OSError(f"Error creating folder {self.__location}: {str(e)}")
    self.__get_cover_art()


  def episodeCount(self) -> int:
    return len(self.__list)


  def subscribe(self, window) -> None:
    subs = subscriptions()
    if self.__xmlURL in subs:
      logger.info(f'Already Subscribed to {self.__title}')
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Already Subscribed to {self.__title}");')
      return

    subs.append(self.__xmlURL)

    set_key(os.path.join(script_folder, '.env'), 'subscriptions', ','.join(subs))

    if window:
      window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Subscribed!");')
    
    logger.info('Subscribed: Starting download. This may take a minuite.')
    self.downloadNewest(window)


  def unsubscribe(self, window) -> None:
    def go():
      subs = subscriptions()
      if self.__xmlURL in subs:
        updated = [x for x in subs if x != self.__xmlURL]
        set_key(os.path.join(script_folder, '.env'), 'subscriptions', ','.join(updated))
        if window:
          try: 
            shutil.rmtree(self.__location)
            print(f'Deleteing directory {self.__location}')
          except:
            pass
          
    if window:
      go()
      return

    if question(f'is "{self.__title}" the right podcast? (yes/no) '):
      go()
      if question('Remove all downloaded files? (yes/no) ') and question('files can not be recovered. are you sure? (yes/no) '):
        try: 
          shutil.rmtree(self.__location)
          print(f'Deleteing directory {self.__location}')
        except:
          pass


  def downloadNewest(self, window) -> None:
    self.__mkdir()
    self.__fileDL(self.__list[0], self.episodeCount(), window)
    logger.info('download complete')


  def downloadAll(self, window) -> None:
    self.__mkdir()
    for ndx, episode in enumerate(self.__list):
      self.__fileDL(episode, self.episodeCount() - ndx, window)
    logger.info('download complete')


  def downloadCount(self, count, window) -> None:
    self.__mkdir()
    for ndx in range(count):
      self.__fileDL(self.__list[ndx], self.episodeCount() - ndx, window)
    logger.info('download complete')



if __name__ == "__main__":
  try:
    if len(sys.argv) > 1:
      podcast_url:str = sys.argv[1]
      action:str = sys.argv[2] if len(sys.argv) > 2 else ''

      sub = ['subscribe', 'sub', 's']
      unsub = ['unsubscribe', 'unsub', 'u']
      

      while True:
        answer = action if action != '' else input("Please choose: subscribe or unsubscribe: ")
        if answer.lower() in sub:
          Podcast(podcast_url).subscribe(False)
          break
        elif answer.lower() in unsub:
          Podcast(podcast_url).unsubscribe(False)
          break
        else:
          print('Invalid option. Please enter subscribe or unsubscribe.')
    else:
      raise IndexError("Updating podcasts.")

  except IndexError as e:
    try:
      for url in subscriptions():
        Podcast(url).downloadNewest(False)
    except Exception as e:
      logger.error(f"Error downloading podcast: {e}")
