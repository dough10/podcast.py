import os

def subscriptions():
  """
  Fetches the list of subscribed podcast URLs from the .env file.
  
  Returns:
    List of podcast URLs (str).
  """
  sub_list: str = os.getenv('subscriptions', '')
  return sub_list.split(',') if sub_list else []