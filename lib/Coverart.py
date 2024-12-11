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

  def __init__(self, url:str) -> None:
    try:
      logger.debug(f'Fetching image from: {url}')
      response = requests.get(url, headers=headers)
      response.raise_for_status()

      if not 'content-type' in response.headers and not 'image' in response.headers['content-type']:
        raise Exception(f'Not valid image content-type: {self.__img.headers["content-type"]}')

      self.__img = Image.open(BytesIO(response.content))

      width, height = self.__img.size

      if width > 1000 or height > 1000:
        logger.debug(f'Resizing image: {width}px X {height}px -> 1000px X 1000px')
        self.__img.thumbnail((1000, 1000), Image.LANCZOS)

      if self.__img.mode != 'RGB':
        logger.debug(f'Convertings image mode: {self.__img.mode} -> RGB')
        self.__img = self.__img.convert('RGB')    

    except requests.exceptions.RequestException as e:
      raise DownloadError(f'Error getting image data from {url}: {e}')
    except Exception as e:
      raise DownloadError(f'Unexpected error: {e}')
  
  def save(self, path:str) -> None:
    self.__cover_path = os.path.join(path, 'cover.jpg')

    if os.path.exists(self.__cover_path):
      logger.debug(f'{self.__cover_path} exists')
      return

    try:
      logger.info(f'Saving cover art to: {self.__cover_path}')
      self.__img.save(self.__cover_path, 'JPEG')
    except OSError as e:
      raise Exception(f'Can not save cover image as JPG: {e}')
    
  def bytes(self) -> bytes:
    bytes = BytesIO()
    self.__img.save(bytes, format='JPEG')
    logger.debug('Generating image bytes')
    return bytes.getvalue()
