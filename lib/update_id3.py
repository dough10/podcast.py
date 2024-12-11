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


get_ep_number_from_title = [
  'Hospital Records Podcast'
]

def number_is_not_year(num):
  return num < 2000

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
  except IOError as e:
    raise IOError(f"Error creating temp file: {str(e)}")
  except Exception as e:
    raise Exception(f"Error saving image to tempfile: {str(e)}")

def load_saved_image(location:str) -> bytes:
  logger.debug(f'Opening file from: {location}')
  try:
    img = Image.open(location)
    if img.mode != 'RGB':
      logger.debug(f'Converting {location} image mode: {img.mode} -> RGB')
      img = img.convert('RGB')
    
    img_bytes = BytesIO()
    img.save(img_bytes, format='JPEG')
    return img_bytes.getvalue()
  
  except IOError as e:
    raise IOError(f"Error loading {location}: {str(e)}")
      
  except Exception as e:
    raise Exception(f"Unexpected error while processing {location}: {str(e)}")

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
  tmp_file_path = None
  try:
    file['artwork'] = art
  except KeyError as e:
    logger.error(f"Error accessing 'artwork' in ID3 file: {str(e)}")
  except Exception as e:
    logger.error('Error setting ID3 artwork:', str(e))
    try:
      logger.debug(f'Attempting temp_file workaround')
      tmp_file_path:str = save_image_to_tempfile(art)
      if tmp_file_path:
        file['artwork'] = load_saved_image(tmp_file_path)
        logger.info('Using workaround for embedding image.')
      else:
        logger.error("Failed to create temporary image file for workaround.")
    
    except IOError as e:   
      raise IOError(f'IOError creating temp_file: {e}')
     
    except Exception as e:
      raise Exception('Error using image temp_file workaround:', str(e))
      
      
    finally:
      try:
        if tmp_file_path and os.path.exists(tmp_file_path):
          os.remove(tmp_file_path)
          logger.debug(f"Cleaned up temporary image file at {tmp_file_path}")
      except OSError as e:
        logger.error(f"Error cleaning up temporary image file {tmp_file_path}: {str(e)}")
        raise 

def update_ID3(podcast_title:str, episode:dict, path:str, epNum, use_fallback_image):
  try:
    logger.info('Updating ID3 tags & encoding artwork')
    file = id3.load_file(path)
  except FileNotFoundError:
    logger.error(f'Error: file {path} not found')
    raise
    
  except id3.exceptions.FileFormatError:
    raise Exception(f"Error: The file format of '{path}' is not supported or the file is corrupted.")
    
  except Exception as e:
    raise Exception(f"Error loading ID3 file: {str(e)}")
    

  file['title'] = format_filename(episode['title'])
  file['album'] = podcast_title
  file['artist'] = podcast_title
  file['genre'] = 'Podcast'
  file['album artist'] = 'Various Artist'


  # Set comment tag if 'itunes:subtitle' key exists
  try:
    file['comment'] = episode['itunes:subtitle']
  except KeyError as e:
    logger.error(f'Failed to set comment: {str(e)}')


  # Set year tag
  pub_date = None
  try:
    pub_date = datetime.datetime.strptime(episode['pubDate'], '%a, %d %b %Y %H:%M:%S %z')
  except (ValueError, TypeError) as E:
    try:
      pub_date = datetime.datetime.strptime(episode['pubDate'], '%a, %d %b %Y %H:%M:%S %Z')
    except (ValueError, TypeError) as e:
      logger.error(f"Error setting year tag: {str(E)}, {str(e)}")

  if pub_date:
    file['year'] = pub_date.year


  # Set track number
  try:
    # return list of numbers in episode title (looking for "actual" episode number)
    numbers_in_string:list[int] = [int(s) for s in re.findall(r'\b\d+\b', episode['title'])]

    if podcast_title in get_ep_number_from_title:
      for num in numbers_in_string:
        if number_is_not_year(num):
          logger.debug(f'Using episode number from title: {num}')
          file['tracknumber'] = num

    if not file['tracknumber']:
      try:
        if 'itunes:episode' in episode:
          logger.debug(f'Using episode number from XML: {episode['itunes:episode']}')
          file['tracknumber'] = episode['itunes:episode']
        else:
          logger.debug(f'Using episode number from episode count: {epNum}')
          file['tracknumber'] = epNum
      except Exception as e:
        raise Exception(e)
  except Exception as e:
    logger.error(f"Error setting track number: {str(e)}")


  # Set ID3 artwork
  try:
    if 'itunes:image' in episode:
      # If the episode metadata contains an 'itunes:image' key
      url = episode['itunes:image']['@href']

      img = requests.get(url)
      img.raise_for_status()

      logger.debug(f'itunes:image: {url}, status_code: {img.status_code}')

      # Check if the image retrieval was successful
      if 'content-type' in img.headers and 'image' in img.headers['content-type']:
        try:
          # Open the image using PIL
          img = Image.open(BytesIO(img.content))

          # Convert image to RGB mode if it's in RGBA mode
          if img.mode != 'RGB':
            logger.debug(f'Cnverting image mode: {img.mode} -> RGB')
            img = img.convert('RGB')

          bytes = BytesIO()
          img.save(bytes, format='JPEG')
  
          id3Image(file, bytes.getvalue())
        except Exception as e:
          logger.error(f'Failed setting image from {url}: {e}')
          use_fallback_image(file)
      else:
        # If retrieval failed, use a fallback image or previously loaded image
        use_fallback_image(file)
    else:
      # If episode metadata does not contain 'itunes:image' key
      use_fallback_image(file)
        
  except Exception as e:
    # Handle any exceptions that occur during setting ID3 artwork
    raise Exception(f"Error setting ID3 artwork: {str(e)}")

  # Save the modified ID3 tags
  try:
    file.save()
  except Exception as e:
    raise Exception(f"Error saving ID3 tags: {str(e)}")
