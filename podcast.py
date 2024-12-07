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

file_path:str = os.path.abspath(__file__)
script_folder:str = os.path.dirname(file_path)



class Podcast:

  def __init__(self, url:str):
    # check internet
    if not is_connected():
      logger.error('Error connecting to the internet. Please check network connection and try again')
      sys.exit()
      
    self.__podcast_folder:str = os.getenv('podcast_folder', 'episodes')

    if not os.path.exists(self.__podcast_folder):
      logger.error(f'Folder {self.__podcast_folder} does not exist. check .env')
      sys.exit()

    self.__xmlURL:str = url.strip()

    if not is_valid_url(self.__xmlURL):
      logger.error('Invalid URL address')
      sys.exit()

    if not is_live_url(self.__xmlURL):
      logger.error(f'Error connecting to {self.__xmlURL}')
      sys.exit()
      
    time_stamp:str = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')

    logger.info(time_stamp)
    logger.info(f'Fetching XML from {self.__xmlURL}')

    res = requests.get(self.__xmlURL, headers=headers)
    if res.status_code != 200:
      logger.error(f'Error getting XML data. Error code {res.status_code}')
      sys.exit()
    try:
      xml = xmltodict.parse(res.content)
    except Exception as e:
      logger.error(f'Error parsing XML {e}')
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
    logger.info(f'{self.__title} {str(self.episodeCount())} episodes')


  def fallback_image(self, file):
    logger.info('using fallback image')
    if hasattr(self, '__image'):
      id3Image(file, self.__image)
    else:
      self.__image = load_saved_image(self.__coverJPG)
      id3Image(file, self.__image)


  def __fileDL(self, episode, epNum, window):
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
      # if window:
      #   window.evaluate_js(f'document.querySelector("audiosync-podcasts").update("{self.__xmlURL}", {downloaded}, {total}, {start_time}, "{stats['filename']}")')
    
    path:str = os.path.join(self.__podcast_folder, stats['path'])

    # check if the file exists
    if os.path.isfile(path):
      logger.info(f'Episode {stats["filename"]} already downloaded')
      return
    
    logger.info(f'Downloading - {stats["filename"]}')
    # download the file and update ui with progress
    dlWithProgressBar(stats['url'], path, progress_callback=prog_update)
    # tag file with info
    update_ID3(self.__title, episode, path, epNum, self.fallback_image)


  def __get_cover_art(self):
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


  def __mkdir(self):
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


  def episodeCount(self):
    return len(self.__list)


  def subscribe(self, window):
    if self.__xmlURL in []:
      print(f'Already Subscribed to {self.__title}')
      # if window:
      #   window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Already Subscribed to {self.__title}");')
      return

    # add url to config file
    # config_controler.subscribe(self.__xmlURL)

    # if window:
    #   window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Subscribed!");')
    
    print('Starting download. This may take a minuite.')
    self.downloadNewest(window)


  def unsubscribe(self, window):
    def go():
      if self.__xmlURL in []:
        pass
        # config_controler.unsubscribe(self.__xmlURL)
        # if window:
        #   try: 
        #     shutil.rmtree(self.__location)
        #     print(f'Deleteing directory {self.__location}')
        #   except:
        #     pass
          
    # if window:
    #   go()
    #   return

    if question(f'is "{self.__title}" the right podcast? (yes/no) '):
      go()
      if question('Remove all downloaded files? (yes/no) ') and question('files can not be recovered. are you sure? (yes/no) '):
        try: 
          shutil.rmtree(self.__location)
          print(f'Deleteing directory {self.__location}')
        except:
          pass

  def downloadNewest(self, window):
    self.__mkdir()
    self.__fileDL(self.__list[0], self.episodeCount(), window)
    logger.info('download complete')


  def downloadAll(self, window):
    self.__mkdir()
    for ndx, episode in enumerate(self.__list):
      self.__fileDL(episode, self.episodeCount() - ndx, window)
    logger.info('download complete')


  def downloadCount(self, count, window):
    self.__mkdir()
    for ndx in range(count):
      self.__fileDL(self.__list[ndx], self.episodeCount() - ndx, window)
    logger.info('download complete')





if __name__ == "__main__":

  def subscriptions():
    sub_list:str = os.getenv('subscriptions', '')
    return sub_list.split(',') if sub_list else []


  try:
    Podcast(sys.argv[1]).downloadNewest(False)
  except IndexError:
    try:
      for url in subscriptions():
        Podcast(url).downloadNewest(False)
    except Exception as e:
      print(e)