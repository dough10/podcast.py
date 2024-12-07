import re
import os
import datetime
import requests
import tempfile
from PIL import Image
import music_tag as id3
from io import BytesIO

try:
  from logs import Logs
  from format_filename import format_filename
except ModuleNotFoundError:
  from lib.logs import Logs
  from lib.format_filename import format_filename

logger = Logs().get_logger()


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
      logger.error(f"Error saving image to tempfile: {str(e)}")
      return None

def load_saved_image(location:str) -> bytes:
  if os.path.exists(location):
    try:
      img = Image.open(location)
      if img.mode == 'RGBA':
        img = img.convert('RGB')
      bytes = BytesIO()
      img.save(bytes, format='JPEG')
      return bytes.getvalue()
    except Exception as e:
      logger.error(f'Error loading {location}:', str(e)) 


# write an Image to audiofile ID3 info
def id3Image(file, art):
  """
  Sets the ID3 artwork for the given file using the provided image data.

  Args:
      file (id3.ID3): The ID3 file object.
      img (bytes): The image data.

  Returns:
      None
  """
  try:
    file['artwork'] = art
  except Exception as e:
    logger.error('Error setting ID3 artwork:', str(e))
    try:
      tmp_file_path = save_image_to_tempfile(art)
      logger.debug(f'attempting temp_image workaround: {e}')
      if tmp_file_path:
        file['artwork'] = load_saved_image(tmp_file_path)
        logger.info('Using workaround for embedding image.')
    except Exception as e:
      logger.error('Error in workaround:', str(e))
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
    logger.error(f"Error setting track number: {str(e)}")


def update_ID3(podcast_title:str, episode:dict, path:str, epNum, use_fallback_image):
  try:
    file = id3.load_file(path)
  except Exception as e:
    logger.info(f"Error loading ID3 file: {str(e)}")
    return
  
  try:
    logger.info('Updating ID3 tags & encoding artwork')
    file['title'] = format_filename(episode['title'])
    file['album'] = podcast_title
    file['artist'] = podcast_title
    file['genre'] = 'Podcast'
    file['album artist'] = 'Various Artist'

    # Set comment tag if 'itunes:subtitle' key exists
    if 'itunes:subtitle' in episode:
      file['comment'] = episode['itunes:subtitle']

    # Set year tag
    date_str:str = datetime.datetime.strptime(episode['pubDate'], '%a, %d %b %Y %H:%M:%S %z')
    try:
      pub_date = date_str
    except (ValueError, TypeError):
      try:
        pub_date = date_str
      except (ValueError, TypeError) as e:
        logger.error(f"Error setting year tag: {str(e)}")
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
      logger.error(f"Error setting track number: {str(e)}")

    # Set ID3 artwork
    try:
      if 'itunes:image' in episode:
        # If the episode metadata contains an 'itunes:image' key
        url = episode['itunes:image']['@href']

        img = requests.get(url)

        logger.debug(f'itunes:image: {url}, status_code: {img.status_code}')

        # Check if the image retrieval was successful
        if img.status_code == 200 and 'content-type' in img.headers and 'image' in img.headers['content-type']:
          try:
            # Open the image using PIL
            img = Image.open(BytesIO(img.content))

            # Convert image to RGB mode if it's in RGBA mode
            logger.debug(f'image mode: {img.mode}')
            if img.mode == 'RGBA':
              img = img.convert('RGB')

            bytes = BytesIO()
            img.save(bytes, format='JPEG')
   
            # Set ID3 artwork using the retrieved image data
            file['artwork'] = bytes.getvalue()
          except Exception as e:
            logger.error(f'shit happened: {e}')
            use_fallback_image(file)
        else:
          # If retrieval failed, use a fallback image or previously loaded image
          use_fallback_image(file)
      else:
        # If episode metadata does not contain 'itunes:image' key
        use_fallback_image(file)
          
    except Exception as e:
      # Handle any exceptions that occur during setting ID3 artwork
      logger.error(f"Error setting ID3 artwork: {str(e)}")

    # Save the modified ID3 tags
    try:
      file.save()
    except Exception as e:
      logger.error(f"Error saving ID3 tags: {str(e)}")
  except Exception as e:
    logger.error(f"Error updating ID3 tags: {str(e)}")