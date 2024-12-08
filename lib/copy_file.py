import os
import time
import shutil

try:
  from logs import Logs
except ModuleNotFoundError:
  from lib.logs import Logs

logger = Logs().get_logger()

def copy_file(source:str, destination:str, path:str, max_retries=5, timeout=10) -> None:
  """
  Copy a file from the source path to the destination path with retries.

  Parameters:
  - source (str): The source file path.
  - destination (str): The destination directory path.
  - path (str): The complete destination path for the copied file.
  - max_retries (int): Maximum number of copy retries.
  - timeout (int): Timeout duration between retries.

  Returns:
  None
  """
  if os.path.exists(path):
    return
  retries = 0
  while retries < max_retries:
    try:
      logger.info(f'Copy: {source} -> {path}')
      shutil.copy2(source, destination)
      # change_log.file_wrote()
      break
    except PermissionError:
      retries += 1
      if retries < max_retries:
        time.sleep(timeout)
      else:
        logger.info(f"{path} Maximum retries reached. Copy failed.")
        raise
    except FileNotFoundError as e:
      logger.critical('error copying missing file:', e)
    except shutil.Error as e:
      logger.info(f"Error copying file: {str(e)}")
      retries += 1
      if retries < max_retries:
        logger.info(f"Retrying after {timeout} seconds...")
        time.sleep(timeout)
      else:
        logger.info(f"{path} Maximum retries reached. Copy failed.")
        raise