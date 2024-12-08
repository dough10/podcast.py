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

# Importing various helper functions and modules
from lib.question import question
from lib.format_filename import format_filename
from lib.headers import headers
from lib.update_id3 import update_ID3, id3Image, load_saved_image
from lib.logs import Logs
from lib.download import dlWithProgressBar
from lib.podcast_episode_exists import podcast_episode_exists
from lib.is_live_url import is_live_url, is_connected, is_valid_url

# Initialize logger
logger = Logs().get_logger()

# Load environment variables from .env file
load_dotenv()

# Get the absolute path of the script file and the folder containing it
file_path = os.path.abspath(__file__)
script_folder = os.path.dirname(file_path)

# Function to return the list of subscribed podcasts from environment variables
def subscriptions():
  """
  Fetches the list of subscribed podcast URLs from the .env file.
  
  Returns:
    List of podcast URLs (str).
  """
  sub_list: str = os.getenv('subscriptions', '')
  return sub_list.split(',') if sub_list else []

# Main Podcast class for handling podcast operations like subscribing, downloading, etc.
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
    # Check internet connection before proceeding
    if not is_connected():
      logger.critical('Error connecting to the internet. Please check network connection and try again')
      sys.exit()

    # Set podcast folder from .env
    self.__podcast_folder: str = os.getenv('podcast_folder')

    # Check if the podcast folder exists, if not exit the program
    if not os.path.exists(self.__podcast_folder):
      logger.critical(f'Folder {self.__podcast_folder} does not exist. Check .env')
      sys.exit()

    # Clean up and store the RSS feed URL
    self.__xmlURL: str = url.strip()

    # Validate the URL
    if not is_valid_url(self.__xmlURL):
      logger.error(f'Invalid URL address: {self.__xmlURL}')
      sys.exit()

    # Check if the URL is live and reachable
    if not is_live_url(self.__xmlURL):
      logger.error(f'Error connecting to {self.__xmlURL}')
      sys.exit()

    # Log the current timestamp
    time_stamp: str = datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
    logger.info(time_stamp)

    # Fetch podcast XML feed
    logger.info(f'Fetching data from: {self.__xmlURL}')
    res = requests.get(self.__xmlURL, headers=headers)
    if res.status_code != 200:
      logger.critical(f'Error getting XML data. Error code {res.status_code}')
      sys.exit()

    # Parse the XML content
    try:
      xml = xmltodict.parse(res.content)
    except Exception as e:
      logger.critical(f'Failed parsing XML: {e}')
      sys.exit()

    # Extract podcast title and episode list from the XML
    self.__title: str = xml['rss']['channel']['title']  # Podcast title
    self.__list: list[dict] = xml['rss']['channel']['item']  # List of episodes
    self.__location: str = os.path.join(self.__podcast_folder, format_filename(self.__title))  # Folder path for the podcast

    # Extract cover image URL (handle different XML structures)
    try:
      self.__imgURL: str = xml['rss']['channel']['image']['url']
    except TypeError:
      self.__imgURL: str = xml['rss']['channel']['image'][0]['url']
    except KeyError:
      self.__imgURL: str = xml['rss']['channel']['itunes:image']['@href']

    logger.info(f'{self.__title}: {str(self.episodeCount())} episodes')

  def fallback_image(self, file) -> None:
    """
    Handles the fallback image (in case the main cover art is not available) 
    and sets it as the ID3 image for the podcast file.

    Args:
      file (str): Path to the downloaded podcast file.
    """
    logger.info('Using fallback image')
    if hasattr(self, '__image'):
      id3Image(file, self.__image)  # Update the ID3 tags with the image
    else:
      self.__image = load_saved_image(self.__coverJPG)  # Load a saved image if available
      id3Image(file, self.__image)  # Update the ID3 tags with the image

  def __fileDL(self, episode, epNum, window) -> None:
    """
    Downloads a podcast episode and applies ID3 tags to the downloaded file.
    
    Args:
      episode (dict): The metadata of the episode (from the XML).
      epNum (int): The episode number.
      window (object): UI window for progress updates (if applicable).
    """
    stats = podcast_episode_exists(self.__title, episode)

    # Check if the episode has already been downloaded
    if stats['exists']:
      logger.info(f'Episode {stats["filename"]} already downloaded')
      return

    # Ensure the file path is correctly formatted
    if stats['path'].startswith('\\') or stats['path'].startswith('/'):
      stats['path'] = stats['path'][1:]

    # Update progress on the UI (if window is passed)
    def prog_update(downloaded, total, start_time):
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").update("{self.__xmlURL}", {downloaded}, {total}, {start_time}, "{stats["filename"]}")')

    # Prepare the path to save the downloaded episode
    path: str = os.path.join(self.__podcast_folder, stats['path'])

    logger.info(f'Downloading - {stats["filename"]}')
    # Download the episode with progress reporting
    dlWithProgressBar(stats['url'], path, progress_callback=prog_update)

    # Apply ID3 tags to the downloaded file
    update_ID3(self.__title, episode, path, epNum, self.fallback_image)

  def __get_cover_art(self) -> None:
    """
    Downloads and saves the podcast cover art if it is not already saved.
    The cover art is saved as 'cover.jpg' in the podcast's folder.
    """
    self.__coverJPG: str = os.path.join(self.__location, 'cover.jpg')

    # If cover art is not available, download it
    if not os.path.exists(self.__coverJPG):
      logger.info(f'Saving cover art {self.__coverJPG}')
      res = requests.get(self.__imgURL, headers=headers)
      if res.status_code == 200:
        img = Image.open(BytesIO(res.content))
      else:
        logger.error("Failed to fetch image:", res.status_code)
        return
      logger.info(f'Image format: {img.format}, Mode: {img.mode}, Size: {img.size}')
      width, height = img.size
      # Resize image if too large
      if width > 1000 or height > 1000:
        img.thumbnail((1000, 1000), Image.LANCZOS)
      img.convert('RGB')
      try:
        img.save(self.__coverJPG, 'JPEG')
      except OSError:
        img.save(self.__coverJPG, 'PNG')
      self.__image = img  # Save the image for later use

  def __mkdir(self) -> None:
    """
    Creates the directory for the podcast if it doesn't exist.
    Also, fetches and saves the cover art for the podcast.
    """
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

    # Fetch cover art for the podcast
    self.__get_cover_art()

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
    if self.__xmlURL in subs:
      logger.info(f'Already Subscribed to {self.__title}')
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Already Subscribed to {self.__title}");')
      return

    subs.append(self.__xmlURL)

    # Update the subscription list in the .env file
    set_key(os.path.join(script_folder, '.env'), 'subscriptions', ','.join(subs))

    if window:
      window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Subscribed!");')
    
    logger.info('Subscribed: Starting download. This may take a minute.')
    # Start downloading the newest episode
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
      if self.__xmlURL in subs:
        updated = [x for x in subs if x != self.__xmlURL]
        set_key(os.path.join(script_folder, '.env'), 'subscriptions', ','.join(updated))
        if window:
          try:
            shutil.rmtree(self.__location)
            logger.info(f'Deleting directory {self.__location}')
          except:
            pass

    # Execute unsubscription process
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
          pass

  def downloadNewest(self, window) -> None:
    """
    Downloads the newest episode from the podcast.
    
    Args:
      window (object): UI window for progress updates (if applicable).
    """
    self.__mkdir()  # Ensure the directory and cover art exist
    self.__fileDL(self.__list[0], self.episodeCount(), window)  # Download the newest episode

  def downloadAll(self, window) -> None:
    """
    Downloads all episodes from the podcast.
    
    Args:
      window (object): UI window for progress updates (if applicable).
    """
    self.__mkdir()
    for ndx, episode in enumerate(self.__list):
      self.__fileDL(episode, self.episodeCount() - ndx, window)

  def downloadCount(self, count, window) -> None:
    """
    Downloads a specific number of episodes from the podcast.
    
    Args:
      count (int): The number of episodes to download.
      window (object): UI window for progress updates (if applicable).
    """
    self.__mkdir()
    for ndx in range(count):
      self.__fileDL(self.__list[ndx], self.episodeCount() - ndx, window)


if __name__ == "__main__":
  try:
    if len(sys.argv) > 1:
      podcast_url: str = sys.argv[1]
      action: str = sys.argv[2] if len(sys.argv) > 2 else ''

      sub = ['subscribe', 'sub', 's']
      unsub = ['unsubscribe', 'unsub', 'u']

      # Prompt for user action if needed
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
      # Download newest episodes for all subscriptions
      for url in subscriptions():
        Podcast(url).downloadNewest(False)
    except Exception as e:
      logger.error(f"Error downloading podcast: {e}")
