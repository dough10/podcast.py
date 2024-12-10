import os
from urllib.parse import urlparse

try:
  from format_filename import format_filename
except ModuleNotFoundError:
  from lib.format_filename import format_filename


def podcast_episode_exists(podcast_title:str, episode):
  folder = os.getenv('podcast_folder')

  # URL!!!
  download_url:str = episode['enclosure']['@url']

  # download file extension
  file_ext:str = os.path.splitext(urlparse(download_url).path)[-1]

  try:
    filename:str = format_filename(f"S{episode['itunes:season']}.E{episode['itunes:episode']}.{episode['title']}{file_ext}")
  except KeyError:
    filename:str = format_filename(f"{episode['title']}{file_ext}")
  
  filename:str = filename.replace(' ','.')
  location:str = os.path.join(folder, format_filename(podcast_title))
  path:str = os.path.join(location, filename)
  
  return {
    'exists': os.path.exists(path) and os.path.isfile(path), 
    'path': path.replace(folder, ''), 
    'filename': filename, 
    'url': download_url
  }