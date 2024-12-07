import time
import requests
from tqdm import tqdm

try:
  from logs import Logs
  from headers import headers
except ModuleNotFoundError:
  from lib.logs import Logs
  from lib.headers import headers

logger = Logs().get_logger()

class DownloadError(Exception):
  """Custom exception for download errors"""
  pass

def dlWithProgressBar(url: str, path: str, progress_callback=None, max_retries=3):
  chunk_size = 4096
  retries = 0

  while retries < max_retries:
    try:
      session = requests.Session()
      media = session.get(url, stream=True, headers=headers)
      media.raise_for_status()  # Raise an exception for any HTTP errors (status code >= 400)

      total_bytes = int(media.headers.get('content-length', 0))
      bytes_downloaded = 0
      start_time = round(time.time() * 1000)
      progress = tqdm(total=total_bytes, unit='iB', unit_scale=True)

      with open(path, 'wb', buffering=chunk_size) as file:
        for data in media.iter_content(chunk_size):
          bytes_downloaded += len(data)
          file.write(data)
          progress.update(len(data))
          if progress_callback:
            progress_callback(bytes_downloaded, total_bytes, start_time)

      progress.close()

      if bytes_downloaded != total_bytes:
        logger.error("ERROR: Incomplete download detected.")
        raise DownloadError("Incomplete download.")

      return  # Exit the loop if download is successful

    except requests.exceptions.RequestException as e:
      retries += 1
      logger.error(f"ERROR: An error occurred during the download: {str(e)} (Retry {retries}/{max_retries})")

      if retries >= max_retries:
        logger.error(f"ERROR: Maximum retries reached. Download failed.")
        raise DownloadError(f"Download failed after {max_retries} retries.")  # Raising a custom exception
      time.sleep(2)  # Optionally, wait before retrying

    except IOError as e:
      logger.error(f"ERROR: An I/O error occurred while writing the file: {str(e)}")
      raise DownloadError("I/O error during file write.")

    except DownloadError as de:
      logger.error(f"ERROR: {str(de)}")
      raise
