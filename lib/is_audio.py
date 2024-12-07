from lib.audio_formats import audio_formats

def is_audio_file(file:str):
  return any(file.lower().endswith(ext) for ext in audio_formats)