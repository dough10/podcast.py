try:
  from logs import Logs
except ModuleNotFoundError:
  from lib.logs import Logs

logger = Logs().get_logger()

# request yes, no / true, false input from user
def question(q):
  while True:
    answer = input(q).strip().lower()
    if answer in ['yes', 'y', '1']:
      return True
    elif answer in ['no', 'n', '0']:
      return False
    else:
      logger.info('Invalid option. Please enter "yes" or "no".')