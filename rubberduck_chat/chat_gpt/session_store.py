import collections
import json
import os
import shelve
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
from uuid import uuid4

from rubberduck_chat.store import rubberduck_dir_name
from rubberduck_chat.utils import get_datetime

gpt_dir_name = 'gpt'
gpt_cache_name = 'gpt-cache'
gpt_sessions_dir_name = 'sessions'


class GptRole(Enum):
  SYSTEM = 'system'
  USER = 'user'
  ASSISTANT = 'assistant'


@dataclass
class Session:
  session_id: str
  last_active_time: int


class GptSessionMetadata:
  def __init__(self, session_id: str, created_time: int):
    self.id = session_id
    self.created_time = created_time

  @classmethod
  def from_line(cls, line: str):
    message = json.loads(line)
    session_id = message.get('id')
    created_time = message.get('created_time')
    return cls(session_id, created_time)

  def get_line(self) -> str:
    return json.dumps({
      'id': self.id,
      'created_time': self.created_time
    })


class GptSystemMessage:
  def __init__(self, system_message_id: str, created_time: int, content: str):
    self.id = system_message_id
    self.created_time: int = created_time
    self.content: str = content

  @classmethod
  def from_system_message(cls, content: str):
    return cls(str(uuid4()), int(time.time()), content)

  @classmethod
  def from_json_string(cls, line: str):
    message = json.loads(line)
    system_message_id = message.get('id')
    created_time = int(message.get('created_time'))
    content = message.get('content')
    return cls(system_message_id, created_time, content)

  def get_json_string(self) -> str:
    return json.dumps({
      'id': self.id,
      'created_time': self.created_time,
      'content': self.content
    })

  def get_chat_gpt_request_message(self) -> dict:
    return {
      'role': 'system',
      'content': self.content
    }


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


def remove_old_sessions(max_sessions):
  session_dir = get_gpt_session_dir_path()
  session_files = os.listdir(session_dir)
  session_files_and_timestamps: List[tuple[str, int]] = []

  if max_sessions == 0:
    for session_file in session_files:
      os.remove(get_gpt_session_filepath(session_file))
    return

  for session_file in session_files:
    session_file_path = get_gpt_session_filepath(session_file)
    with open(session_file_path, 'r') as file_handle:
      last_line = collections.deque(file_handle, 1)[0]
      chat_turn = GptChatTurn.from_json_string(last_line)
      session_files_and_timestamps.append((session_file, chat_turn.created_time))

  session_files_and_timestamps.sort(key=lambda pair: pair[1])
  files_to_remove = session_files_and_timestamps[max_sessions:]
  current_session = get_active_session()

  for session_file_and_timestamp in files_to_remove:
    session_file = session_file_and_timestamp[0]

    # Do not remove the current session, even if it is old enough to be removed.
    # This ensures that the user can continue their session.
    if current_session and session_file == current_session.session_id:
      continue

    os.remove(get_gpt_session_filepath(session_file))


def get_all_session_previews() -> List[GptSessionPreview]:
  filenames = os.listdir(get_gpt_session_dir_path())
  previews: List[GptSessionPreview] = []
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


def fetch_session_data(session_id: str) -> List[str]:
  with open(get_gpt_session_filepath(session_id), 'r') as file:
    return file.readlines()


def store_metadata_to_file(session_id: str, message: GptSessionMetadata):
  with open(get_gpt_session_filepath(session_id), 'a') as file:
    file.write(f'{message.get_line()}\n')


def store_system_message_to_file(session_id: str, message: GptSystemMessage):
  with open(get_gpt_session_filepath(session_id), 'a') as file:
    file.write(f'{message.get_json_string()}\n')


def store_chat_turn_to_file(session_id: str, message: GptChatTurn):
  with open(get_gpt_session_filepath(session_id), 'a') as file:
    file.write(f'{message.to_json_string()}\n')


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
