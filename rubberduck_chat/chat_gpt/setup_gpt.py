import os
import time
from typing import Optional

from rubberduck_chat.chat_gpt.chat import GptChat, GptChatSession
from rubberduck_chat.chat_gpt.credentials import setup_gpt_credentials
from rubberduck_chat.chat_gpt.session_store import get_gpt_dir_path, get_gpt_session_dir_path, \
  create_get_gpt_session_dir, remove_old_sessions, get_active_session, get_preview_for_session, set_active_session_id
from rubberduck_chat.configs import config_collection


def setup_gpt(openai_api_key: Optional[str]) -> GptChat:
  max_saved_session_count = int(config_collection.max_saved_session_count.get_value())

  os.makedirs(get_gpt_dir_path(), exist_ok=True)
  os.makedirs(get_gpt_session_dir_path(), exist_ok=True)

  setup_gpt_credentials(openai_api_key)
  create_get_gpt_session_dir()
  remove_old_sessions(max_saved_session_count)
  previous_session = restore_previous_session()

  if previous_session:
    return GptChat(previous_session)
  else:
    return GptChat(get_new_session())


def restore_previous_session() -> Optional[GptChatSession]:
  always_continue_last_session = config_collection.always_continue_last_session.get_value() == 'True'
  active_session = get_active_session()

  if always_continue_last_session and active_session:
    return GptChatSession.from_session_id(active_session.session_id)

  if active_session:
    old_session_cutoff_time_in_seconds = int(config_collection.inactive_session_cutoff_time_in_seconds.get_value())
    is_active_session_expired = int(
      time.time()) - old_session_cutoff_time_in_seconds > active_session.last_active_time

    if not is_active_session_expired:
      return GptChatSession.from_session_id(active_session.session_id)

  return None


def get_new_session() -> Optional[GptChatSession]:
  session = GptChatSession.create_new()
  set_active_session_id(session.session_id)
  return session


def print_session_preview_message(session: GptChatSession):
  if session.turns:
    session_preview = get_preview_for_session(session.session_id)
    if session_preview:
      print(f'Continuing from session: {session_preview.session_preview}')
  else:
    print('Started new session')
