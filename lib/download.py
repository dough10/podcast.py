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

def bytes_to_readable_size(bytes: int) -> str:
  """
  Converts the given size in bytes to a human-readable format (KB, MB, GB, etc.).

  Args:
    bytes (int): The size in bytes to convert.

  Returns:
    str: A formatted string representing the size in a readable format (KB, MB, GB, etc.).
  
  Example:
    >>> bytes_to_readable_size(1048576)
    '1.00 MB'
  """
  # Define the size thresholds and their corresponding units
  units = ['B', 'KB', 'MB', 'GB', 'TB']
  
  # Start with bytes and find the appropriate unit
  unit_index = 0
  size = bytes
  
  while size >= 1024 and unit_index < len(units) - 1:
    size /= 1024.0
    unit_index += 1

  # Format the size to two decimal places and append the unit
  return f"{size:.2f} {units[unit_index]}"


def bytes_to_readable_rate(rate: float) -> str:
  """
  Converts a download rate in bytes per second to a human-readable format (KB/s, MB/s, GB/s).

  Args:
    rate (float): The download rate in bytes per second.

  Returns:
    str: A formatted string representing the download rate in a readable format.
  
  Example:
    >>> bytes_to_readable_rate(1048576)
    '1.00 MB/s'
  """
  # Define the size thresholds and their corresponding units
  units = ['B/s', 'KB/s', 'MB/s', 'GB/s', 'TB/s']
  unit_index = 0
  
  # Loop to find the appropriate unit for the rate
  while rate >= 1024 and unit_index < len(units) - 1:
    rate /= 1024.0
    unit_index += 1

  # Format the rate to two decimal places and append the unit
  return f"{rate:.2f} {units[unit_index]}"


def seconds_to_readable_time(seconds: int) -> str:
  """
  Converts time from seconds to a human-readable format (hours, minutes, and seconds).

  Args:
    seconds (int): Time in seconds to convert.

  Returns:
    str: A formatted string representing the time in hours, minutes, and seconds.
  
  Example:
    >>> seconds_to_readable_time(3661)
    '1 hour, 1 minute, 1 second'
  """
  hours = seconds // 3600
  minutes = (seconds % 3600) // 60
  seconds = seconds % 60

  time_str = []
  if hours > 0:
    time_str.append(f"{hours} hour{'s' if hours > 1 else ''}")
  if minutes > 0:
    time_str.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
  if seconds > 0 or (hours == 0 and minutes == 0):
    time_str.append(f"{seconds} second{'s' if seconds != 1 else ''}")
  
  return ', '.join(time_str)


def dl_with_progress_bar(url: str, path: str, progress_callback=None, max_retries=3):
  """
  Downloads a file from the specified URL and shows a progress bar. It retries the download in case of errors.

  Args:
    url (str): The URL of the file to download.
    path (str): The local path where the file should be saved.
    progress_callback (function, optional): A callback function that will be called with the download progress.
    max_retries (int, optional): The maximum number of retries in case of a download failure.

  Raises:
    DownloadError: If the download fails after retrying or if an error occurs during the download process.

  Example:
    dl_with_progress_bar('https://example.com/file.mp3', '/path/to/save/file.mp3')
  """
  chunk_size = 4096  # Size of each chunk of data to download
  retries = 0  # Counter for retry attempts

  while retries < max_retries:
    try:
      # Start a new session for the download
      session = requests.Session()
      media = session.get(url, stream=True, headers=headers)
      media.raise_for_status()  # Raise an exception if HTTP status code >= 400

      total_bytes = int(media.headers.get('content-length', 0))  # Get the total file size
      bytes_downloaded = 0  # Variable to track downloaded bytes
      start_time = round(time.time() * 1000)  # Record the start time in milliseconds

      # Create a progress bar for the download
      progress = tqdm(total=total_bytes, unit='iB', unit_scale=True)

      # Open the file and write chunks of data to it
      with open(path, 'wb', buffering=chunk_size) as file:
        for data in media.iter_content(chunk_size):
          chunk_length = len(data)
          bytes_downloaded += chunk_length  # Update the number of bytes downloaded
          file.write(data)  # Write the chunk to the file
          progress.update(chunk_length)  # Update the progress bar
          
          # Call the progress callback, if provided
          if progress_callback:
            progress_callback(bytes_downloaded, total_bytes, start_time)

      progress.close()  # Close the progress bar when done

      # Log total size and download rate after closing the progress bar
      if total_bytes > 0:
        elapsed_time = (round(time.time() * 1000) - start_time) / 1000  # Time in seconds
        download_rate = total_bytes / elapsed_time
        logger.info(f"Download completed: {bytes_to_readable_size(total_bytes)} MB downloaded. "
                    f"Elapsed time: {seconds_to_readable_time(elapsed_time)}. "
                    f"Average download rate: {bytes_to_readable_rate(download_rate)}.")

      # Check if the downloaded bytes match the expected total
      if bytes_downloaded != total_bytes:
        logger.error("ERROR: Incomplete download detected.")
        raise DownloadError("Incomplete download.")

      return  # Exit the loop if download is successful

    except requests.exceptions.RequestException as e:
      retries += 1  # Increment retry counter
      logger.error(f"ERROR: An error occurred during the download: {str(e)} (Retry {retries}/{max_retries})")

      # Retry if the max retries have not been reached
      if retries >= max_retries:
        logger.error(f"ERROR: Maximum ({max_retries}) retries reached. Download failed.")
        raise DownloadError(f"Download failed after {max_retries} retries.")
      
      # Wait before retrying
      time.sleep(2)

    except IOError as e:
      logger.error(f"ERROR: An I/O error occurred while writing the file: {str(e)}")
      raise DownloadError("I/O error during file write.")

    except DownloadError as de:
      logger.error(f"ERROR: {str(de)}")
      raise  # Re-raise the custom download error
