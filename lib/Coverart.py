import os
import requests
from PIL import Image
from io import BytesIO

try:
  from headers import headers
  from logs import Logs
  from download import DownloadError
except ModuleNotFoundError:
  from lib.headers import headers
  from lib.logs import Logs
  from lib.download import DownloadError

logger = Logs().get_logger()

class Coverart:

  def __init__(self, url:str = '' , location:str = '') -> None:
    try:
      if url:
        logger.debug(f'Downloading: {url}')
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        if not 'content-type' in response.headers and not 'image' in response.headers['content-type']:
          raise Exception(f'Not valid image content-type: {response.headers["content-type"]}')

        self.__img = Image.open(BytesIO(response.content))

      elif location:
        logger.debug(f'Loading: {location}')
        self.__img = Image.open(location)
      
      else: 
        raise Exception('No content provided')

      width, height = self.__img.size

      if width > 1000 or height > 1000:
        logger.debug(f'Resizing: {width}px X {height}px -> 1000px X 1000px')
        self.__img.thumbnail((1000, 1000), Image.LANCZOS)

      if self.__img.mode != 'RGB':
        logger.debug(f'Converting: {self.__img.mode} -> RGB')
        self.__img = self.__img.convert('RGB')    

    except requests.exceptions.RequestException as e:
      raise DownloadError(f'Error getting image data: {e}')
    except Exception as e:
      raise DownloadError(f'Unexpected error: {e}')
  
  def save(self, path:str) -> None:
    self.__cover_path = os.path.join(path, 'cover.jpg')

    if os.path.exists(self.__cover_path):
      return

    try:
      logger.info(f'Saving: {self.__cover_path}')
      self.__img.save(self.__cover_path, 'JPEG')
    except OSError as e:
      raise Exception(f'Can not save cover image as JPG: {e}')
    
  def bytes(self) -> bytes:
    logger.debug('Generating image bytes')
    bytes = BytesIO()
    self.__img.save(bytes, format='JPEG')
    return bytes.getvalue()
