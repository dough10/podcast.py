def get_image_url(xml:dict) -> str:
  """Extracts the image URL from the given XML data.

  Args:
    xml: The XML data, likely a parsed XML object.

  Returns:
    The extracted image URL, or None if not found.
  """
  try:
    if isinstance(xml['rss']['channel']['image'], list):
      return xml['rss']['channel']['image'][0]['url']
    
    return xml['rss']['channel']['image']['url']

  except KeyError:
    pass

  try:
    return xml['rss']['channel']['itunes:image']['@href']
  except KeyError:
    return None