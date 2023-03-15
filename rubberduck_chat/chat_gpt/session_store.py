import collections
import json
import os
import shelve
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from rubberduck_chat.store import rubberduck_dir_name
from rubberduck_chat.utils import get_datetime

gpt_dir_name = 'gpt'
gpt_cache_name = 'gpt-cache'
gpt_sessions_dir_name = 'sessions'
active_session_filename_suffix = 'ACTIVE'


class GptRole(Enum):
  SYSTEM = 'system'
  USER = 'user'
  ASSISTANT = 'assistant'


def convert_string_to_gpt_role(string: str) -> GptRole:
  return GptRole[string.upper()]


@dataclass
class Session:
  filename: str
  last_active_time: int


@dataclass
class GptMessage:
  def __init__(self, created_time: int, role: GptRole, content: str):
    self.created_time: int = created_time
    self.role: GptRole = role
    self.content: str = content

  @classmethod
  def from_line(cls, line: str):
    message = json.loads(line)
    created_time = int(message.get('created_time'))
    role = convert_string_to_gpt_role(message.get('role'))
    content = message.get('content')
    return cls(created_time, role, content)

  def get_message(self) -> dict:
    return {
      'role': self.role.value,
      'content': self.content
    }

  def get_line(self) -> str:
    return json.dumps({
      'created_time': self.created_time,
      'role': self.role.value,
      'content': self.content
    })


class GptSessionMetadata:
  def __init__(self, created_time: int):
    self.created_time = created_time

  @classmethod
  def from_line(cls, line: str):
    message = json.loads(line)
    created_time = message.get('created_time')
    return cls(created_time)

  def get_line(self) -> str:
    return json.dumps({
      'created_time': self.created_time
    })


class GptSystemMessage:
  def __init__(self, system_message: GptMessage):
    self.system_message: GptMessage = system_message

  @classmethod
  def from_system_message(cls, system_message: str):
    return cls(GptMessage(int(time.time()), GptRole.SYSTEM, system_message))


class GptChatTurn:
  def __init__(self, user_prompt: GptMessage, assistant_response: Optional[GptMessage]):
    self.user_prompt: GptMessage = user_prompt
    self.assistant_response: Optional[GptMessage] = assistant_response

  @classmethod
  def from_user_prompt(cls, message: str):
    return cls(GptMessage(int(time.time()), GptRole.USER, message), None)

  def updated_assistant_response(self, message: str):
    self.assistant_response = GptMessage(int(time.time()), GptRole.ASSISTANT, message)

  def updated_assistant_response_with_message(self, message: GptMessage):
    self.assistant_response = message


@dataclass
class GptSessionPreview:
  session_preview: str
  session_filename: str


def get_gpt_dir_path() -> str:
  home_dir = os.path.expanduser('~')
  return os.path.join(home_dir, rubberduck_dir_name, gpt_dir_name)


def get_gpt_dir_filepath(filename: str) -> str:
  home_dir = os.path.expanduser('~')
  return os.path.join(home_dir, rubberduck_dir_name, gpt_dir_name, filename)


def get_gpt_session_dir_path() -> str:
  home_dir = os.path.expanduser('~')
  return os.path.join(home_dir, rubberduck_dir_name, gpt_dir_name, gpt_sessions_dir_name)


def get_gpt_session_filepath(filename: str) -> str:
  home_dir = os.path.expanduser('~')
  return os.path.join(home_dir, rubberduck_dir_name, gpt_dir_name, gpt_sessions_dir_name, filename)


def create_get_gpt_session_dir():
  os.makedirs(get_gpt_session_dir_path(), exist_ok=True)


def cleanup_old_sessions(max_session_count):
  filenames = os.listdir(get_gpt_session_dir_path())
  filenames_and_latest_message_time: list[tuple[str, int]] = []

  for filename in filenames:
    with open(get_gpt_session_filepath(filename), 'r') as file:
      last_line = collections.deque(file, 1)[0]
      message = GptMessage.from_line(last_line)
      filenames_and_latest_message_time.append((filename, message.created_time))

  filenames_and_latest_message_time.sort(key=lambda tu: tu[1])
  files_to_delete = filenames_and_latest_message_time[max_session_count:]
  active_session = get_active_session()

  for filename_and_time in files_to_delete:
    filename = filename_and_time[0]

    # Do no remove active session, even if it old enough to be cleanup. This is to make sure the use can have a session
    # to continue from
    if active_session and filename == active_session.filename:
      continue

    os.remove(get_gpt_session_filepath(filename))


def get_all_session_previews() -> list[GptSessionPreview]:
  filenames = os.listdir(get_gpt_session_dir_path())
  previews: list[GptSessionPreview] = []
  active_session = get_active_session()

  for filename in filenames:
    if active_session and active_session.filename == filename:
      maybe_preview = get_active_session_preview_from_session_file(filename)
    else:
      maybe_preview = get_preview_from_session_file(filename)

    if maybe_preview:
      previews.append(maybe_preview)

  previews.sort(key=lambda preview: preview.session_preview, reverse=True)

  return previews


def get_active_session_preview_from_session_file(session_filename) -> Optional[GptSessionPreview]:
  user_prompt = get_most_recent_user_prompt(session_filename)

  if user_prompt:
    preview = f'[{get_datetime(user_prompt.created_time)}] [Current Session] {user_prompt.content}'
    return GptSessionPreview(preview, session_filename)
  else:
    return None


def get_preview_from_session_file(session_filename) -> Optional[GptSessionPreview]:
  user_prompt = get_most_recent_user_prompt(session_filename)

  if user_prompt:
    return GptSessionPreview(f'[{get_datetime(user_prompt.created_time)}] {user_prompt.content}', session_filename)
  else:
    return None


def get_most_recent_user_prompt(session_filename: str) -> Optional[GptMessage]:
  with open(get_gpt_session_filepath(session_filename), 'r') as file:
    last_two_lines = collections.deque(file, 2)

    if len(last_two_lines) >= 2:
      second_prompt = GptMessage.from_line(last_two_lines[1])
      if second_prompt.role == GptRole.USER:
        return second_prompt

    if len(last_two_lines) >= 1:
      first_prompt = GptMessage.from_line(last_two_lines[0])
      if first_prompt.role == GptRole.USER:
        return first_prompt

  return None


def fetch_session_data(session_filename: str) -> list[str]:
  with open(get_gpt_session_filepath(session_filename), 'r') as file:
    return file.readlines()


def store_metadata_to_file(session_filename: str, message: GptSessionMetadata):
  with open(get_gpt_session_filepath(session_filename), 'a') as file:
    file.write(f'{message.get_line()}\n')


def store_message_to_file(session_filename: str, message: GptMessage):
  with open(get_gpt_session_filepath(session_filename), 'a') as file:
    file.write(f'{message.get_line()}\n')


def create_session_filename() -> str:
  return str(uuid.uuid4())


def unset_active_session():
  with shelve.open(get_gpt_dir_filepath(gpt_cache_name)) as shelf:
    shelf['active_session_filename'] = ''


def set_active_session_filename(active_session_filename: str):
  with shelve.open(get_gpt_dir_filepath(gpt_cache_name)) as shelf:
    shelf['active_session_filename'] = active_session_filename
    shelf['active_session_last_active_time'] = int(time.time())


def get_active_session() -> Optional[Session]:
  with shelve.open(get_gpt_dir_filepath(gpt_cache_name)) as shelf:
    if 'active_session_filename' not in shelf or 'active_session_last_active_time' not in shelf:
      return None

    active_session_filename = str(shelf['active_session_filename'])
    active_session_time = int(str(shelf['active_session_last_active_time']))

    if len(active_session_filename) > 0 and os.path.exists(get_gpt_session_filepath(active_session_filename)):
      return Session(active_session_filename, active_session_time)
    else:
      return None
