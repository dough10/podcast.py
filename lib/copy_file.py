import os
import time
import shutil

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
      # log(f'Copy: {source} -> {path}')
      shutil.copy2(source, destination)
      # change_log.file_wrote()
      break  # Copy successful, exit the loop
    except PermissionError:
      retries += 1
      if retries < max_retries:
        time.sleep(timeout)
      else:
        # log(f"{path} Maximum retries reached. Copy failed.")
        raise  # Reraise the exception if maximum retries reached
    except FileNotFoundError as e:
      # print(source)
      print('error copying missing file:', e)
    except shutil.Error as e:
      # log(f"Error copying file: {str(e)}")
      retries += 1
      if retries < max_retries:
        # log(f"Retrying after {timeout} seconds...")
        time.sleep(timeout)
      else:
        # log(f"{path} Maximum retries reached. Copy failed.")
        raise  # Reraise the exception if maximum retries reached