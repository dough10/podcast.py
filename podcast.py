#!/usr/bin/env python3

import os
import sys
import shutil
import requests
import xmltodict
from dotenv import load_dotenv, set_key

from lib.Coverart import Coverart
from lib.question import question
from lib.format_filename import format_filename
from lib.headers import headers
from lib.update_id3 import update_ID3, id3Image
from lib.logs import Logs
from lib.download import dl_with_progress_bar
from lib.podcast_episode_exists import podcast_episode_exists
from lib.is_live_url import is_live_url, is_connected, is_valid_url
from lib.get_image_url import get_image_url
from lib.subscriptions import subscriptions

logger = Logs().get_logger()

load_dotenv()

file_path = os.path.abspath(__file__)
script_folder = os.path.dirname(file_path)

class Podcast:
  """
  A class to represent a podcast and handle related operations like
  downloading episodes, updating ID3 tags, fetching cover art, etc.
  """

  def __init__(self, url: str) -> None:
    """
    Initialize a Podcast instance by validating the URL, checking connection,
    and parsing the XML feed to extract podcast metadata.
    
    Args:
      url (str): The URL to the podcast RSS feed.
    """
    if not is_connected():
      raise Exception('Error connecting to the internet. Please check network connection and try again')

    self.__podcast_folder: str = os.getenv('podcast_folder')

    if not os.path.exists(self.__podcast_folder):
      raise Exception(f'Folder {self.__podcast_folder} does not exist. Check .env')

    self.__xml_url: str = url.strip()

    if not is_valid_url(self.__xml_url):
      raise Exception(f'Invalid URL address: {self.__xml_url}')

    if not is_live_url(self.__xml_url):
      raise Exception(f'Error connecting to: {self.__xml_url}')

    try:
      logger.debug(f'Fetching data from: {self.__xml_url}')
      res = requests.get(self.__xml_url, headers=headers)
      res.raise_for_status()
      xml = xmltodict.parse(res.content)

      self.__title: str = xml['rss']['channel']['title']  # Podcast title
      self.__list: list[dict] = xml['rss']['channel']['item']  # List of episodes
      self.__location: str = os.path.join(self.__podcast_folder, format_filename(self.__title))  # Folder path for the podcast


      self.__img_url: str = get_image_url(xml)
      if not self.__img_url:
        raise Exception(f'Failed to find an image url in xml data')

      logger.info(f'{self.__title}: {str(self.episodeCount())} episodes')

    except requests.exceptions.RequestException as e:
      raise Exception(f'Error getting XML data from {self.__xml_url}: {e}')
    except ValueError as e:
      raise Exception(f'Failed parsing XML from {self.__xml_url}: {e}')
    except Exception as e:
      raise Exception(f'Unexpected error: {e}')
    
  def __fallback_image(self, file) -> None:
    """
    Handles the fallback image (in case the main cover art is not available) 
    and sets it as the ID3 image for the podcast file.

    Args:
      file (str): Path to the downloaded podcast file.
    """
    logger.debug('Using fallback image')
    if hasattr(self, '__img'):
      try:
        id3Image(file, self.__img.bytes())
      except Exception as e:
        logger.error(f'Failed setting image from __img variable: {e}')
        self.__img = None
        self.__fallback_image(file)
    else:
      try:
        self.__img = Coverart(location=os.path.join(self.__location, 'cover.jpg'))
        id3Image(file, self.__img.bytes())
      except Exception as e:
        logger.error(f'Failed to load art from file: {e}')

  def __fileDL(self, episode, epNum, window) -> None:
    """
    Downloads a podcast episode and applies ID3 tags to the downloaded file.
    
    Args:
      episode (dict): The metadata of the episode (from the XML).
      epNum (int): The episode number.
      window (object): UI window for progress updates (if applicable).
    """
    try:
      stats = podcast_episode_exists(self.__title, episode)
    except Exception as e:
      logger.debug(episode)
      logger.critical(f'Failed checking episode status: {e}')
      return

    if stats['exists']:
      logger.info(f'{stats["filename"]} already downloaded')
      return

    if stats['path'].startswith('\\') or stats['path'].startswith('/'):
      stats['path'] = stats['path'][1:]

    def prog_update(downloaded, total, start_time):
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").update("{self.__xml_url}", {downloaded}, {total}, {start_time}, "{stats["filename"]}")')

    path: str = os.path.join(self.__podcast_folder, stats['path'])

    logger.info(f'Downloading - {stats["filename"]}')
    try:
      dl_with_progress_bar(stats['url'], path, progress_callback=prog_update)
    except Exception as e:
      logger.error(f'Failed to download file: {str(e)}')
      return

    try:
      update_ID3(self.__title, episode, path, epNum, self.__fallback_image)
    except Exception as e:
      logger.error(f'Failed setting ID3 info: {str(e)}')
      return

  def __mkdir(self) -> None:
    """
    Creates the directory for the podcast if it doesn't exist.
    Also, fetches and saves the cover art for the podcast.
    """
    if not os.path.exists(self.__podcast_folder):
      raise Exception(f'Error accessing location {self.__podcast_folder}, Check if drive is mounted')

    if not os.path.exists(self.__location):
      logger.debug(f'Creating folder {self.__location}')
      try:
        os.makedirs(self.__location)
      except OSError as e:
        raise OSError(f"Error creating folder {self.__location}: {str(e)}")

  def __get_cover(self):
    cover_loc = os.path.join(self.__location, 'cover.jpg')
    if not os.path.exists(cover_loc):
      try: 
        self.__img = Coverart(url=self.__img_url)
        self.__img.save(self.__location)
      except Exception as e:
        raise Exception(e)

  def episodeCount(self) -> int:
    """
    Returns the number of episodes in the podcast feed.
    
    Returns:
      int: Number of episodes in the podcast feed.
    """
    return len(self.__list)

  def subscribe(self, window) -> None:
    """
    Subscribes to the podcast by adding it to the subscription list
    and starts downloading the newest episode.
    
    Args:
      window (object): UI window for progress updates (if applicable).
    """
    subs = subscriptions()
    if self.__xml_url in subs:
      logger.info(f'Already Subscribed to {self.__title}')
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Already Subscribed to {self.__title}");')
      return

    subs.append(self.__xml_url)

    set_key(os.path.join(script_folder, '.env'), 'subscriptions', ','.join(subs))

    logger.info('Subscribed!')
    if window:
      window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Subscribed!");')
    elif question('Download newest episode? (y,n): '):
      self.downloadNewest(window)

  def unsubscribe(self, window) -> None:
    """
    Unsubscribes from the podcast by removing it from the subscription list
    and optionally deleting the downloaded files.
    
    Args:
      window (object): UI window for progress updates (if applicable).
    """
    def go():
      subs = subscriptions()
      if self.__xml_url in subs:
        updated = [url for url in subs if url != self.__xml_url]
        set_key(os.path.join(script_folder, '.env'), 'subscriptions', ','.join(updated))
        if window:
          try:
            shutil.rmtree(self.__location)
            logger.info(f'Deleting directory {self.__location}')
          except:
            pass

    if window:
      go()
      return

    if question(f'is "{self.__title}" the right podcast? (yes/no) '):
      go()
      if question('Remove all downloaded files? (yes/no) ') and question('Files cannot be recovered. Are you sure? (yes/no) '):
        try:
          shutil.rmtree(self.__location)
          logger.info(f'Deleting directory {self.__location}')
        except:
          logger.error(f'Failed deletion: {self.__location}')

  def downloadNewest(self, window) -> None:
    """
    Downloads the newest episode from the podcast.
    
    Args:
      window (object): UI window for progress updates (if applicable).
    """
    try:
      self.__mkdir()
    except Exception as e:
      logger.critical(f'Error creating directory: {e}')
      return

    try:
      self.__get_cover()
    except Exception as e:
      logger.critical(f'Failed getting cover.jpg: {e}')
      return

    self.__fileDL(self.__list[0], self.episodeCount(), window)

  def downloadAll(self, window) -> None:
    """
    Downloads all episodes from the podcast.
    
    Args:
      window (object): UI window for progress updates (if applicable).
    """
    try:
      self.__mkdir()
    except Exception as e:
      logger.critical(f'Error creating directory: {e}')
      return

    try:
      self.__get_cover()
    except Exception as e:
      logger.critical(f'Failed getting cover.jpg: {e}')
      return

    for ndx, episode in enumerate(self.__list):
      self.__fileDL(episode, self.episodeCount() - ndx, window)

  def downloadCount(self, count, window) -> None:
    """
    Downloads a specific number of episodes from the podcast.
    
    Args:
      count (int): The number of episodes to download.
      window (object): UI window for progress updates (if applicable).
    """
    try:
      self.__mkdir()
    except Exception as e:
      logger.critical(f'Error creating directory: {e}')
      return

    try:
      self.__get_cover()
    except Exception as e:
      logger.critical(f'Failed getting cover.jpg: {e}')
      return

    for ndx in range(count):
      self.__fileDL(self.__list[ndx], self.episodeCount() - ndx, window)

def main() -> None:
  try:
    if len(sys.argv) > 1:
      podcast_url: str = sys.argv[1]
      action: str = sys.argv[2] if len(sys.argv) > 2 else None

      options = {
        "1": lambda: Podcast(podcast_url).subscribe(False),
        "2": lambda: Podcast(podcast_url).unsubscribe(False),
        "3": lambda: Podcast(podcast_url).downloadAll(False),
        "4": lambda: Podcast(podcast_url).downloadNewest(False)
      }

      while True:
        answer = action if action else input("Choose an option: subscribe: 1, unsubscribe: 2, download all: 3, download newest: 4 - ")
        if answer in options:
          options[answer]()
          break
        else:
          action = None
          print('Invalid option. Please enter 1-4.')
          
    else:
      subs = subscriptions()

      for url in subs:
        Podcast(url).downloadNewest(False)
        
      if not len(subs):
        logger.info('No subscriptions found.')

  except Exception as e:
    logger.critical(f'Failed running podcast.py: {e}')

  except KeyboardInterrupt:
    pass


if __name__ == "__main__":
  main()