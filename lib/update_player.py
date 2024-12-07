# write new podcast episodes to the given directory / player address
import os
import tqdm
import time
import glob
import shutil
import datetime

try:
  from logs import Logs
  from old_date import old_date
  from audio_formats import audio_formats 
  from copy_file import copy_file
  from question import question
  from escape_folder import escape_folder
except ModuleNotFoundError:
  from lib.logs import Logs
  from lib.old_date import old_date
  from lib.audio_formats import audio_formats 
  from lib.copy_file import copy_file
  from lib.question import question
  from lib.escape_folder import escape_folder

logger = Logs().get_logger()

# count audio file in the given directory
def playable_file_count(dir:str) -> int:
  count = 0
  for file_type in audio_formats:
    count += len(glob.glob(os.path.join(dir, f'*{file_type}')))
  return count


# list of files newer than the 'old_date' variable
def list_of_new_files(path:str) -> list[str]:
  return [
    file for file in glob.glob(os.path.join(path, '*.mp3'))
    if old_date < datetime.datetime.fromtimestamp(os.path.getmtime(file)).date()
  ]


# lsit of files older then the 'old_date' variable
def list_of_old_files(path:str) -> list[str]:
  return [
    file for file in glob.glob(os.path.join(path, '*.mp3'))
    if old_date > datetime.datetime.fromtimestamp(os.path.getmtime(file)).date()
  ]


def updatePlayer(player:str, window, bypass=False) -> None:
  start_time = time.time()
  
  folder = os.getenv('podcast_folder')
  
  # check locations exist
  if not os.path.exists(folder):
    raise FileNotFoundError(f"Error accessing {folder}. Check if the drive is mounted")

  if not os.path.exists(player):
    raise FileNotFoundError(f"Error accessing {player}. Check if the drive is mounted")
  
  if not bypass:
    logger.info('Begining sync. This may take a while')

  podcast_folder_on_player = os.path.join(player, 'Podcasts')
  if not os.path.exists(podcast_folder_on_player):
    try:
      os.makedirs(podcast_folder_on_player)
    except OSError as e:
      raise OSError(f"Error creating folder {podcast_folder_on_player}: {str(e)}")

  dirs = [dir for dir in os.listdir(folder) if not dir.startswith('.')]

  length = len(dirs)
  last_ndx = 0
  # copy/remove files
  for ndx, dir in enumerate(tqdm(dirs, desc='Updating Podcasts', unit='podcast')):
    src:str = os.path.join(folder, dir) # where all the files are located
    src_art:str = os.path.join(src, 'cover.jpg')
    dest:str = os.path.join(podcast_folder_on_player, dir) # where we will send the files
    dest_art:str = os.path.join(dest, 'cover.jpg')
    files_to_add = list_of_new_files(src)
    files_to_delete = list_of_old_files(dest)
    num_files:int = len(files_to_add)
    # create folder if there are files to write in it
    if not os.path.exists(dest) and num_files > 0:
      try:
        logger(f'Creating folder {dest}')
        os.makedirs(dest)
        # change_log.new_folder()
      except OSError as e:
        raise OSError(f"Error creating folder {dest}: {str(e)}")
      
    # copy cover.jpg
    if not os.path.exists(dest_art) and os.path.exists(dest):
      try:
        copy_file(src_art, dest, dest_art)
        # change_log.file_wrote()
      except Exception as e:
        raise Exception(f"Error copying cover.jpg: {str(e)}")

    # copy "new" files to player from storage location
    add_count = len(files_to_add)
    for i, file in enumerate(files_to_add):
      filename = os.path.basename(file)
      dest_dir = os.path.join(podcast_folder_on_player, dir)
      path = os.path.join(dest_dir, filename)
      if not os.path.exists(path):
        try:
          copy_file(file, dest_dir, path)
          # change_log.file_wrote()
        except Exception as e:
          raise Exception(f"Error copying file {file}: {str(e)}")
        if window:
          last_ndx = (ndx - 1) + ((i + 1) / add_count)
          window.evaluate_js(f'document.querySelector("sync-ui").updateBar("#podcasts-bar", {last_ndx}, {length});')

    # remove "old" files from player
    for file in files_to_delete:
      try:
        logger(f'Remove: {file} -> Trash')
        os.remove(file)
        # change_log.file_deleted()
      except Exception as e:
        raise Exception(f"Error deleting file {file}: {str(e)}")

    # check for and remove any empty folder
    if os.path.exists(dest) and playable_file_count(dest) == 0:
      try:
        hidden_file = os.path.join(dest, '._cover.jpg')
        if os.path.exists(hidden_file):
          os.remove(hidden_file)
          # change_log.file_deleted()
        logger(f'Removing empty folder {dest}')
        shutil.rmtree(dest)
        # change_log.folder_deleted()
        # change_log.folder_contained(1) # cover.jpg
      except Exception as e:
        raise Exception(f"Error deleting directory {dest}: {str(e)}")
    
    if window and ndx != last_ndx:
      window.evaluate_js(f'document.querySelector("sync-ui").updateBar("#podcasts-bar", {ndx}, {length});')

  # remove folders no longer in source directory (unsubscribed podcast)
  for dir in os.listdir(podcast_folder_on_player):
    dest = os.path.join(podcast_folder_on_player, dir) 
    if not dir.startswith('.') and not dir in os.listdir(folder):
      # change_log.folder_contained(nonhidden_file_count(dest))
      try:
        logger(f'deleting - {dest}')
        shutil.rmtree(dest)
        # change_log.folder_deleted()
      except Exception as e:
        raise Exception(f"Error deleting folder {dest}: {str(e)}")

  if bypass:
    return 
  
  # logger.info(change_log.print(time.time() - start_time))
  
  if question(f'Would you like to eject {player} (yes/no) '):
    logger.warning('Please wait for prompt before removing the drive')
    os.system(f'diskutil eject {escape_folder(player)}')