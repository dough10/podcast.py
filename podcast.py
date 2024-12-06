import os
import re
import sys
import time
import glob
import shutil
import requests
import datetime
import tempfile
import xmltodict
from tqdm import tqdm
from PIL import Image
from io import BytesIO
import music_tag as id3
from urllib.parse import urlparse
# from lib.old_date import old_date
# from lib.is_audio import supported_formats
# from lib.file_manager import File_manager
# from lib.config_controler import Config
# from lib.change_log import ChangeLog

# change_log = ChangeLog()


# fm = File_manager()
# copy_file = fm.copy_file

# config_controler = Config()

file_path = os.path.abspath(__file__)
script_folder = os.path.dirname(file_path)


# folder = config_controler.get_key('podcast_folder')

headers = {
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# check internet connections status
def is_connected():
  return is_live_url("https://google.com")

# make sure URL is a valie URL scheme
def validate_url(url):
  try:
    parsed_url = urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])
  except Exception:
    return False

# make sure URL returns 200 status
def is_live_url(url):
  try:
    response = requests.get(url, timeout=5, headers=headers )
    return response.status_code == 200
  except requests.exceptions.RequestException:
    return False

# list of files newer than the 'old_date' variable
def list_of_new_files(path):
  return [
    file for file in glob.glob(os.path.join(path, '*.mp3'))
    if old_date < datetime.datetime.fromtimestamp(os.path.getmtime(file)).date()
  ]

# lsit of files older then the 'old_date' variable
def list_of_old_files(path):
  return [
    file for file in glob.glob(os.path.join(path, '*.mp3'))
    if old_date > datetime.datetime.fromtimestamp(os.path.getmtime(file)).date()
  ]

# count audio file in the given directory
def playable_file_count(dir):
  count = 0
  for file_type in supported_formats:
    count += len(glob.glob(os.path.join(dir, f'*{file_type}')))
  return count

# count file not hidden
def nonhidden_file_count(dest):
  return len([entry for entry in os.listdir(dest) if os.path.isfile(os.path.join(dest, entry)) and not entry.startswith('.')])

# write new podcast episodes to the given directory / player address
def updatePlayer(player, window, bypass=False, logger=print):
  start_time = time.time()
  
  global folder
  folder = config_controler.get_key('podcast_folder')
  
  # check locations exist
  if not os.path.exists(folder):
    raise FileNotFoundError(f"Error accessing {folder}. Check if the drive is mounted")

  if not os.path.exists(player):
    raise FileNotFoundError(f"Error accessing {player}. Check if the drive is mounted")
  
  if not bypass:
    print('Begining sync. This may take a while')

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
    src = os.path.join(folder, dir) # where all the files are located
    src_art = os.path.join(src, 'cover.jpg')
    dest = os.path.join(podcast_folder_on_player, dir) # where we will send the files
    dest_art = os.path.join(dest, 'cover.jpg')
    files_to_add = list_of_new_files(src)
    files_to_delete = list_of_old_files(dest)
    num_files = len(files_to_add)
    # create folder if there are files to write in it
    if not os.path.exists(dest) and num_files > 0:
      try:
        logger(f'Creating folder {dest}')
        os.makedirs(dest)
        change_log.new_folder()
      except OSError as e:
        raise OSError(f"Error creating folder {dest}: {str(e)}")
      
    # copy cover.jpg
    if not os.path.exists(dest_art) and os.path.exists(dest):
      try:
        copy_file(src_art, dest, dest_art)
        change_log.file_wrote()
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
          change_log.file_wrote()
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
        change_log.file_deleted()
      except Exception as e:
        raise Exception(f"Error deleting file {file}: {str(e)}")

    # check for and remove any empty folder
    if os.path.exists(dest) and playable_file_count(dest) == 0:
      try:
        hidden_file = os.path.join(dest, '._cover.jpg')
        if os.path.exists(hidden_file):
          os.remove(hidden_file)
          change_log.file_deleted()
        logger(f'Removing empty folder {dest}')
        shutil.rmtree(dest)
        change_log.folder_deleted()
        change_log.folder_contained(1) # cover.jpg
      except Exception as e:
        raise Exception(f"Error deleting directory {dest}: {str(e)}")
    
    if window and ndx != last_ndx:
      window.evaluate_js(f'document.querySelector("sync-ui").updateBar("#podcasts-bar", {ndx}, {length});')

  # remove folders no longer in source directory (unsubscribed podcast)
  for dir in os.listdir(podcast_folder_on_player):
    dest = os.path.join(podcast_folder_on_player, dir) 
    if not dir.startswith('.') and not dir in os.listdir(folder):
      change_log.folder_contained(nonhidden_file_count(dest))
      try:
        logger(f'deleting - {dest}')
        shutil.rmtree(dest)
        change_log.folder_deleted()
      except Exception as e:
        raise Exception(f"Error deleting folder {dest}: {str(e)}")

  if bypass:
    return 
  
  print(change_log.print(time.time() - start_time))
  
  if question(f'Would you like to eject {player} (yes/no) '):
    print('Please wait for prompt before removing the drive')
    os.system(f'diskutil eject {escapeFolder(player)}')

# list of cronjobs
def listCronjobs():
  return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', os.popen('crontab -l').read())

# make sure file path doesn't contain special chars
def escapeFolder(s):
  return s.replace(' ', '\\ ').replace('(', '\\(').replace(')', '\\)')

# request yes, no / true, false input from user
def question(q):
  while True:
    answer = input(q).strip().lower()
    if answer in ['yes', 'y', '1']:
      return True
    elif answer in ['no', 'n', '0']:
      return False
    else:
      print('Invalid option. Please enter "yes" or "no".')
      
# download the given audiofile url to the giver file path
def dlWithProgressBar(url, path, progress_callback=None):
  chunk_size = 4096
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
      print("ERROR: Incomplete download detected.")
      sys.exit()
  except requests.exceptions.RequestException as e:
    print(f"ERROR: An error occurred during the download: {str(e)}")
    sys.exit()
  except IOError as e:
    print(f"ERROR: An I/O error occurred while writing the file: {str(e)}")
    sys.exit()

# save a downloaded image as a temp file
def save_image_to_tempfile(img):
  try:
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
      if isinstance(img, bytes):
        tmp_file.write(img)
      else:
        img.save(tmp_file, format='JPEG')
      tmp_file_path = tmp_file.name
      return tmp_file_path
  except Exception as e:
      print(f"Error saving image to tempfile: {str(e)}")
      return None

# write an Image to audiofile ID3 info
def id3Image(file, img):
  """
  Sets the ID3 artwork for the given file using the provided image data.

  Args:
      file (id3.ID3): The ID3 file object.
      img (bytes): The image data.

  Returns:
      None
  """
  try:
    file['artwork'] = img
  except Exception as e:
    print('Error setting ID3 artwork:', str(e))
    try:
      tmp_file_path = save_image_to_tempfile(img)
      if tmp_file_path:
        file['artwork'] = load_saved_image(tmp_file_path)
        print('Using workaround for embedding image.')
    except Exception as e:
      print('Error in workaround:', str(e))
    finally:
      if tmp_file_path and os.path.exists(tmp_file_path):
        os.remove(tmp_file_path)

def setTrackNum(file, episode, epNum):
  """
  Sets the track number for the given ID3 file based on the episode's metadata.

  Args:
      file (id3.ID3): The ID3 file object.
      episode (dict): The metadata of the episode.
      epNum (int): The fallback track number.

  Returns:
      None
  """
  try:
    if 'itunes:episode' in episode:
      file['tracknumber'] = episode['itunes:episode']
    else:
      file['tracknumber'] = epNum
  except Exception as e:
    print(f"Error setting track number: {str(e)}")

def load_saved_image(location):
  if os.path.exists(location):
    try:
      img = Image.open(location)
      if img.mode == 'RGBA':
        img = img.convert('RGB')
      bytes = BytesIO()
      img.save(bytes, format='JPEG')
      return bytes.getvalue()
    except Exception as e:
      print(f'Error loading {location}:', str(e)) 

def time_stamp():
  return datetime.datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')


def episodeExists(podcastTitle, episode):
  # URL!!!
  download_url = episode['enclosure']['@url']
  # download file extension
  file_ext = os.path.splitext(urlparse(download_url).path)[-1]
  try:
    filename = fm.formatFilename(f"S{episode['itunes:season']}.E{episode['itunes:episode']}.{episode['title']}{file_ext}").replace(' ','.')
  except KeyError:
    filename = fm.formatFilename(f"{episode['title']}{file_ext}").replace(' ','.')
  __location = os.path.join(folder, fm.formatFilename(podcastTitle))
  path = os.path.join(__location, filename)
  return {
    'exists': os.path.exists(path), 
    'path': path.replace(folder, ''), 
    'filename': filename, 
    'url': download_url
  }

def update_ID3(podcast_title, episode, path, epNum, use_fallback_image):
  try:
    file = id3.load_file(path)
  except Exception as e:
    print(f"Error loading ID3 file: {str(e)}")
    return
  
  try:
    print('Updating ID3 tags & encoding artwork')
    file['title'] = fm.formatFilename(episode['title'])
    file['album'] = podcast_title
    file['artist'] = podcast_title
    file['genre'] = 'Podcast'
    file['album artist'] = 'Various Artist'

    # Set comment tag if 'itunes:subtitle' key exists
    if 'itunes:subtitle' in episode:
      file['comment'] = episode['itunes:subtitle']

    # Set year tag
    try:
      pub_date = datetime.datetime.strptime(episode['pubDate'], '%a, %d %b %Y %H:%M:%S %z')
    except (ValueError, TypeError):
      try:
        pub_date = datetime.datetime.strptime(episode['pubDate'], '%a, %d %b %Y %H:%M:%S %Z')
      except (ValueError, TypeError) as e:
        print(f"Error setting year tag: {str(e)}")
        pub_date = None
    
    if pub_date:
        file['year'] = pub_date.year

    # Set track number
    try:
      # return list of numbers in episode title (looking for "actualy" episode number)
      ep = [int(s) for s in re.findall(r'\b\d+\b', episode['title'])]
      if podcast_title == 'Hospital Records Podcast' and ep and ep[0] < 2000:
        file['tracknumber'] = ep[0]
      else:
        setTrackNum(file, episode, epNum)
    except Exception as e:
      print(f"Error setting track number: {str(e)}")

    # Set ID3 artwork
    try:
      if 'itunes:image' in episode:
        # If the episode metadata contains an 'itunes:image' key
        img = requests.get(episode['itunes:image']['@href'])

        # Check if the image retrieval was successful
        if img.status_code == 200 and 'content-type' in img.headers and 'image' in img.headers['content-type']:
          try:
            # Open the image using PIL
            art = Image.open(img.content)
            # Convert image to RGB mode if it's in RGBA mode
            if art.mode == 'RGBA':
                art = art.convert('RGB')
            # Set ID3 artwork using the retrieved image data
            id3Image(file, art.tobytes())
          except:
            use_fallback_image(file)
        else:
          # If retrieval failed, use a fallback image or previously loaded image
          use_fallback_image(file)
      else:
        # If episode metadata does not contain 'itunes:image' key
        use_fallback_image(file)
          
    except Exception as e:
      # Handle any exceptions that occur during setting ID3 artwork
      print(f"Error setting ID3 artwork: {str(e)}")

    # Save the modified ID3 tags
    try:
      file.save()
    except Exception as e:
      print(f"Error saving ID3 tags: {str(e)}")
  except Exception as e:
    print(f"Error updating ID3 tags: {str(e)}")

class Podcast:

  def __init__(self, url):
    # check internet
    if not is_connected():
      print('Error connecting to the internet. Please check network connection and try again')
      sys.exit()

    global folder
    folder = config_controler.get_key('podcast_folder')

    # check folder exists
    if not os.path.exists(folder):
      print(f'Folder {folder} does not exist. check config.py')
      sys.exit()
      
    self.__xmlURL = url.strip()

    if not validate_url(self.__xmlURL):
      print('Invalid URL address')
      sys.exit()

    if not is_live_url(self.__xmlURL):
      print(f'Error connecting to {self.__xmlURL}')
      sys.exit()
      
    print(time_stamp())
    print(f'Fetching XML from {self.__xmlURL}')
    res = requests.get(self.__xmlURL, headers=headers)
    if res.status_code != 200:
      print(f'Error getting XML data. Error code {res.status_code}')
      sys.exit()
    try:
      xml = xmltodict.parse(res.content)
    except Exception as e:
      print(f'Error parsing XML {e}')
      sys.exit()
    self.__title = xml['rss']['channel']['title']  # the name of the podcast
    self.__list = xml['rss']['channel']['item']  # list of podcast episodes
    self.__location = os.path.join(folder, fm.formatFilename(self.__title))
    try:
      self.__imgURL = xml['rss']['channel']['image']['url']
    except TypeError:
      self.__imgURL = xml['rss']['channel']['image'][0]['url']
    except KeyError:
      self.__imgURL = xml['rss']['channel']['itunes:image']['@href']
    print(f'{self.__title} {str(self.episodeCount())} episodes')

  def fallback_image(self, file):
    print('using fallback image')
    if hasattr(self, '__image'):
      id3Image(file, self.__image)
    else:
      self.__image = load_saved_image(self.__coverJPG)
      id3Image(file, self.__image)

  def __id3tag(self, episode, path, epNum):
    update_ID3(self.__title, episode, path, epNum, self.fallback_image)

  def __fileDL(self, episode, epNum, window):
    """
    Downloads a podcast episode and sets the ID3 tags for the downloaded file.

    Args:
        episode (dict): The metadata of the episode.
        epNum (int): The episode number.

    Returns:
        None
    """
    stats = episodeExists(self.__title, episode)

    # reflect download progress on UI
    def prog_update(downloaded, total, start_time): 
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").update("{self.__xmlURL}", {downloaded}, {total}, {start_time}, "{stats['filename']}")');
    
    path = os.path.join(folder, stats['path'])

    # check if the file exists
    if os.path.isfile(path):
      print(f'Episode {stats['filename']} already downloaded')
      return
    
    print(f'Downloading - {stats['filename']}')
    # download the file and update ui with progress
    dlWithProgressBar(stats['url'], path, progress_callback=prog_update)
    # tag file with info
    self.__id3tag(episode, path, epNum)

  def __get_cover_art(self):
    self.__coverJPG = os.path.join(self.__location, 'cover.jpg')
    if not os.path.exists(self.__coverJPG):
      print(f'getting cover art {self.__coverJPG}')
      res = requests.get(self.__imgURL, headers=headers)
      if res.status_code == 200:
        img = Image.open(BytesIO(res.content))
      else:
        print("Failed to fetch image:", res.status_code)
        return
      print(f'Image format: {img.format}, Mode: {img.mode}, Size: {img.size}')
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
    if not os.path.exists(folder):
      print(f'Error accessing location {folder}')
      print('Check if network drive is mounted')
      sys.exit()
    if not os.path.exists(self.__location):
      print(f'Creating folder {self.__location}')
      try:
        os.makedirs(self.__location)
      except OSError as e:
        raise OSError(f"Error creating folder {self.__location}: {str(e)}")
    self.__get_cover_art()

  def episodeCount(self):
    return len(self.__list)

  def subscribe(self, window):
    if self.__xmlURL in config_controler.get_key('subscriptions'):
      print(f'Already Subscribed to {self.__title}')
      if window:
        window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Already Subscribed to {self.__title}");')
      return

    # add url to config file
    config_controler.subscribe(self.__xmlURL)

    if window:
      window.evaluate_js(f'document.querySelector("audiosync-podcasts").subResponse("Subscribed!");')
    
    print('Starting download. This may take a minuite.')
    self.downloadNewest(window)

  def unsubscribe(self, window):
    def go():
      if (self.__xmlURL in config_controler.get_key('subscriptions')):
        config_controler.unsubscribe(self.__xmlURL)
        if window:
          try: 
            shutil.rmtree(self.__location)
            print(f'Deleteing directory {self.__location}')
          except:
            pass
          
    if window:
      go()
      return

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
    print('download complete')

  def downloadAll(self, window):
    self.__mkdir()
    for ndx, episode in enumerate(self.__list):
      self.__fileDL(episode, self.episodeCount() - ndx, window)
    print('download complete')

  def downloadCount(self, count, window):
    self.__mkdir()
    for ndx in range(count):
      self.__fileDL(self.__list[ndx], self.episodeCount() - ndx, window)
    print('download complete')

if __name__ == "__main__":
  try:
    Podcast(sys.argv[1]).downloadNewest(False)
  except IndexError:
    try:
      for url in config_controler.get_key('subscriptions'):
        Podcast(url).downloadNewest(False)
    except Exception as e:
      print(e)