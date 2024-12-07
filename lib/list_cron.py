import re
import os

def list_cron() -> list[str]:
  return re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', os.popen('crontab -l').read())


if __name__ == '__main__':
  list_cron()