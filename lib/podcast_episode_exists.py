import os
from urllib.parse import urlparse

try:
  from format_filename import format_filename
except ModuleNotFoundError:
  from lib.format_filename import format_filename

def podcast_episode_exists(podcast_title: str, episode: dict) -> dict:
  """
  Checks if a podcast episode file exists in the local storage and returns detailed information about the episode.

  This function constructs the file path based on the provided podcast title and episode information,
  then checks if the episode file exists in the designated podcast folder. It returns a dictionary
  containing whether the episode exists, the file path, the formatted filename, and the download URL.

  Args:
    podcast_title (str): The title of the podcast. Used to generate the folder path for the podcast.
    episode (dict): A dictionary containing metadata of the podcast episode, including:
      - 'enclosure' (dict): Contains the URL to the downloadable episode file.
      - 'itunes:season' (int): Season number of the episode (optional).
      - 'itunes:episode' (int): Episode number of the episode (optional).
      - 'title' (str): The title of the episode.

  Returns:
    dict: A dictionary with the following keys:
      - 'exists' (bool): Indicates whether the episode file exists in the storage.
      - 'path' (str): The relative file path where the episode file is located, from the podcast folder.
      - 'filename' (str): The formatted filename for the episode.
      - 'url' (str): The URL to download the episode.

  Example:
    result = podcast_episode_exists('My Podcast', {
      'enclosure': {'@url': 'https://example.com/episode.mp3'},
      'itunes:season': 1,
      'itunes:episode': 2,
      'title': 'Episode Title'
    })
    print(result)
    # Output:
    # {'exists': True, 'path': '/podcasts/MyPodcast/S01.E02.Episode.Title.mp3', 'filename': 'S01.E02.Episode.Title.mp3', 'url': 'https://example.com/episode.mp3'}
  """
  
  # Get the folder path where podcasts are stored, from environment variables
  folder: str = os.getenv('podcast_folder')
  
  try:
    # Extract the download URL from the episode metadata
    download_url: str = episode['enclosure']['@url']
  except KeyError as e:
    raise Exception(f'Failed getting an episode url from provided data: {e}')
  
  # Extract the file extension from the URL (e.g., .mp3, .m4a)
  file_ext: str = os.path.splitext(urlparse(download_url).path)[-1]

  try:
    # Try to format the filename using season and episode information
    filename: str = format_filename(f"S{episode['itunes:season']}.E{episode['itunes:episode']}.{episode['title']}{file_ext}")
  except KeyError:
    # If no season or episode number exists, just use the episode title and file extension
    filename: str = format_filename(f"{episode['title']}{file_ext}")
  
  # Replace spaces with dots in the filename
  filename: str = filename.replace(' ', '.')
  
  # Create the full directory path for the podcast based on its title
  location: str = os.path.join(folder, format_filename(podcast_title))
  
  # Construct the full path to the episode file
  path: str = os.path.join(location, filename)
  
  # Return a dictionary with the file existence status and additional information
  return {
    'exists': os.path.exists(path) and os.path.isfile(path),  # Check if the file exists and is a file
    'path': path.replace(folder, ''),  # Return the relative path, excluding the podcast folder
    'filename': filename,  # Return the formatted filename
    'url': download_url  # Return the URL to download the episode
  }
