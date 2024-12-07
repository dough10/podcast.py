import requests
from urllib.parse import urlparse

try:
  from headers import headers
except ModuleNotFoundError:
  from lib.headers import headers
  

# make sure URL is a valie URL scheme
def is_valid_url(url:str) -> bool:
  try:
    parsed_url = urlparse(url)
    return all([parsed_url.scheme, parsed_url.netloc])
  except Exception:
    return False


# check internet connections status
def is_connected() -> bool:
  return is_live_url("https://google.com")


# make sure URL returns 200 status
def is_live_url(url:str) -> bool:
  try:
    response = requests.get(url, timeout=5, headers=headers )
    return response.status_code == 200
  except requests.exceptions.RequestException:
    return False