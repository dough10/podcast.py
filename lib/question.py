# request yes, no / true, false input from user
def question(q):
  while True:
    answer = input(q).strip().lower()
    if answer in ['yes', 'y', '1']:
      return True
    elif answer in ['no', 'n', '0']:
      return False
    else:
      print('Invalid option. Please enter "yes" or "no".')