import configparser
import getpass
import os
from typing import Optional

import openai

from rubberduck_chat.chat_gpt.session_store import gpt_dir_name
from rubberduck_chat.store import rubberduck_dir_name

credentials_filename = 'credentials.ini'
default_credentials_section_name = 'default'
credentials = configparser.ConfigParser()


def get_credentials_filepath() -> str:
  return os.path.join(os.path.expanduser('~'), rubberduck_dir_name, gpt_dir_name, credentials_filename)


credentials.read(get_credentials_filepath())


def setup_gpt_credentials(openai_api_key: Optional[str]):

  if openai_api_key:
    openai.api_key = openai_api_key
    return

  if get_openai_api_key() is not None:
    return

  print('Open AI API Key required. You can get one at https://beta.openai.com/account/api-keys.')
  print('Once you have the key, you can set it as an environment variable with the name OPENAI_API_KEY.')
  print('Alternatively, you can set either the key or the path to a file containing the key and it will be stored '
        'for future use.')

  try:
    key = getpass.getpass('Openai API Key: ')
    cache_openai_api_key(key)
    openai.api_key = get_openai_api_key()
  except KeyboardInterrupt:
    exit()


def ask_for_key_input():
  print('Enter empty input to remove key. Press Ctrl+C to cancel.')
  try:
    key = getpass.getpass('Openai API Key: ')
    cache_openai_api_key(key)
    openai.api_key = get_openai_api_key()
  except KeyboardInterrupt:
    print('')


def get_openai_api_key() -> Optional[str]:
  key = get_openai_api_key_from_config()

  if key is not None:
    return key

  key = get_openai_api_key_from_environment()

  if key is not None:
    return key

  return None


def get_openai_api_key_from_environment() -> Optional[str]:
  key = os.environ.get('OPENAI_API_KEY')
  if key is not None:
    return key
  else:
    return None


def cache_openai_api_key(key: str):
  credentials[default_credentials_section_name] = {
    'openai_api_key': key
  }
  with open(get_credentials_filepath(), 'w') as configfile:
    credentials.write(configfile)


def get_openai_api_key_from_config() -> Optional[str]:
  if not os.path.exists(get_credentials_filepath()):
    return None

  key = credentials.get(default_credentials_section_name, 'openai_api_key')
  if key and len(key.strip()) > 0:
    return key
  else:
    return None
