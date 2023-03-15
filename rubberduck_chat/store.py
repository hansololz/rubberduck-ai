import os

rubberduck_dir_name = '.rubberduck'


def setup_rubberduck_dir():
  os.makedirs(os.path.join(os.path.expanduser('~'), rubberduck_dir_name), exist_ok=True)
