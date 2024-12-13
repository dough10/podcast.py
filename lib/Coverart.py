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
  """
  A class responsible for downloading, resizing, and saving image cover art.
  It supports both downloading an image from a URL and loading from a local file.
  Additionally, it ensures that the image meets certain criteria (e.g., size, format) 
  and allows saving it to a specified location or getting it as a byte array.
  """
  def __init__(self, url:str = '' , location:str = '') -> None:
    """
    Initializes the Coverart object by either downloading an image from the given URL 
    or loading it from a specified local location.
    
    Parameters:
    url (str): URL of the image to download (optional).
    location (str): Local file path to the image (optional).
    
    Raises:
    Exception: If neither 'url' nor 'location' are provided, or if the image content is invalid.
    DownloadError: If any error occurs during downloading or processing the image.
    """
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
    """
    Saves the processed image as a 'cover.jpg' file at the specified path.

    Parameters:
    path (str): The directory where the image should be saved.

    Raises:
    Exception: If the image cannot be saved as a JPEG.
    """
    self.__cover_path = os.path.join(path, 'cover.jpg')

    if os.path.exists(self.__cover_path):
      return

    try:
      logger.info(f'Saving: {self.__cover_path}')
      self.__img.save(self.__cover_path, 'JPEG')
    except OSError as e:
      raise Exception(f'Can not save cover image as JPG: {e}')
    
  def bytes(self) -> bytes:
    """
    Returns the image as a byte array in JPEG format.
    
    Returns:
    bytes: The byte representation of the image.
    """
    logger.debug('embedding image bytes')
    bytes = BytesIO()
    self.__img.save(bytes, format='JPEG')
    return bytes.getvalue()
