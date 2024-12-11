import string

def format_filename(name:str) -> str:
  """
  Format the given string to be a valid filename.

  Parameters:
  - s (str): The input string to be formatted.

  Returns:
  str: The formatted filename.
  """
  valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
  filename = ''.join(c for c in name.replace('&', 'and') if c in valid_chars)
  return filename  