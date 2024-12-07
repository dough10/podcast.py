# make sure file path doesn't contain special chars
def escape_folder(s:str):
  return s.replace(' ', '\\ ').replace('(', '\\(').replace(')', '\\)')