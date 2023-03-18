import collections
import json
import os
import shelve
import time
from uuid import uuid4
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
  session_id: str
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
  def __init__(self, turn_id: str, created_time: int, user_prompt: str, response: Optional[dict]):
    self.id: str = turn_id
    self.created_time: int = created_time
    self.user_prompt: str = user_prompt
    self.response: Optional[dict] = response

  @classmethod
  def from_user_prompt(cls, message: str):
    return cls(str(uuid4()), int(time.time()), message, None)

  @classmethod
  def from_json_string(cls, json_string: str):
    json_data = json.loads(json_string)
    turn_id = json_data.get('id')
    created_time = json_data.get('created_time')
    user_prompt = json_data.get('user_prompt')
    response = json_data.get('response', None)
    return cls(turn_id, created_time, user_prompt, response)

  def to_json_string(self) -> str:
    data = {
      'id': self.id,
      'created_time': self.created_time,
      'user_prompt': self.user_prompt,
    }

    if self.response:
      data['response'] = self.response

    return json.dumps(data)

  def updated_response(self, response: Optional[dict]):
    self.response = response

  def get_assistant_response(self) -> Optional[str]:
    if not self.response or 'choices' not in self.response:
      return None

    if len(self.response['choices']) > 0:
      return self.response['choices'][0]['message']['content']
    else:
      return None

  def get_user_prompt_message(self) -> dict:
    return {
      'role': GptRole.USER.value,
      'content': self.user_prompt
    }

  def get_assistant_response_message(self) -> Optional[dict]:
    content = self.get_assistant_response()

    if not content:
      return None

    return {
      'role': GptRole.ASSISTANT.value,
      'content': content
    }


@dataclass
class GptSessionPreview:
  session_preview: str
  session_id: str


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
      turn = GptChatTurn.from_json_string(last_line)
      filenames_and_latest_message_time.append((filename, turn.created_time))

  filenames_and_latest_message_time.sort(key=lambda tu: tu[1])
  files_to_delete = filenames_and_latest_message_time[max_session_count:]
  active_session = get_active_session()

  for filename_and_time in files_to_delete:
    filename = filename_and_time[0]

    # Do no remove active session, even if it old enough to be cleanup. This is to make sure the use can have a session
    # to continue from
    if active_session and filename == active_session.session_id:
      continue

    os.remove(get_gpt_session_filepath(filename))


def get_all_session_previews() -> list[GptSessionPreview]:
  filenames = os.listdir(get_gpt_session_dir_path())
  previews: list[GptSessionPreview] = []
  active_session = get_active_session()

  for filename in filenames:
    if active_session and active_session.session_id == filename:
      maybe_preview = get_active_session_preview_from_session_file(filename)
    else:
      maybe_preview = get_preview_for_session(filename)

    if maybe_preview:
      previews.append(maybe_preview)

  previews.sort(key=lambda preview: preview.session_preview, reverse=True)

  return previews


def get_active_session_preview_from_session_file(session_id) -> Optional[GptSessionPreview]:
  chat_turn = get_most_recent_chat_turn(session_id)

  if chat_turn:
    preview = f'[{get_datetime(chat_turn.created_time)}] [Current Session] {chat_turn.user_prompt}'
    return GptSessionPreview(preview, session_id)
  else:
    return None


def get_preview_for_session(session_id: str) -> Optional[GptSessionPreview]:
  chat_turn = get_most_recent_chat_turn(session_id)

  if chat_turn:
    user_prompt = chat_turn.user_prompt
    return GptSessionPreview(f'[{get_datetime(chat_turn.created_time)}] {chat_turn.user_prompt}', session_id)
  else:
    return None


def get_most_recent_chat_turn(session_id: str) -> Optional[GptChatTurn]:
  with open(get_gpt_session_filepath(session_id), 'r') as file:
    last_line = collections.deque(file, 1)

    if last_line:
      return GptChatTurn.from_json_string(last_line[0])
    else:
      return None


def fetch_session_data(session_id: str) -> list[str]:
  with open(get_gpt_session_filepath(session_id), 'r') as file:
    return file.readlines()


def store_metadata_to_file(session_id: str, message: GptSessionMetadata):
  with open(get_gpt_session_filepath(session_id), 'a') as file:
    file.write(f'{message.get_line()}\n')


def store_message_to_file(session_id: str, message: GptMessage):
  with open(get_gpt_session_filepath(session_id), 'a') as file:
    file.write(f'{message.get_line()}\n')


def store_chat_turn_to_file(session_id: str, message: GptChatTurn):
  with open(get_gpt_session_filepath(session_id), 'a') as file:
    file.write(f'{message.to_json_string()}\n')


def unset_active_session_id():
  with shelve.open(get_gpt_dir_filepath(gpt_cache_name)) as shelf:
    shelf['active_session_id'] = ''


def set_active_session_id(active_session_id: str):
  with shelve.open(get_gpt_dir_filepath(gpt_cache_name)) as shelf:
    shelf['active_session_id'] = active_session_id
    shelf['active_session_last_active_time'] = int(time.time())


def get_active_session() -> Optional[Session]:
  with shelve.open(get_gpt_dir_filepath(gpt_cache_name)) as shelf:
    if 'active_session_id' not in shelf or 'active_session_last_active_time' not in shelf:
      return None

    active_session_id = str(shelf['active_session_id'])
    active_session_time = int(str(shelf['active_session_last_active_time']))

    if len(active_session_id) > 0 and os.path.exists(get_gpt_session_filepath(active_session_id)):
      return Session(active_session_id, active_session_time)
    else:
      return None
