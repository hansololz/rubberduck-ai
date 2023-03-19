import os
import time
from typing import Optional

from rubberduck_chat.chat_gpt.chat import GptChat, GptChatSession, GptChatSessionConfigs
from rubberduck_chat.chat_gpt.credentials import setup_gpt_credentials
from rubberduck_chat.chat_gpt.session_store import get_gpt_dir_path, get_gpt_session_dir_path, \
  create_get_gpt_session_dir, remove_old_sessions, get_active_session, get_preview_for_session, set_active_session_id
from rubberduck_chat.configs import config_collection


def setup_gpt(openai_api_key: Optional[str]) -> GptChat:
  max_saved_session_count = config_collection.max_saved_session_count.get_int_value()

  os.makedirs(get_gpt_dir_path(), exist_ok=True)
  os.makedirs(get_gpt_session_dir_path(), exist_ok=True)

  setup_gpt_credentials(openai_api_key)
  chat_session_configs = get_gpt_chat_configs()
  create_get_gpt_session_dir()
  remove_old_sessions(max_saved_session_count)
  previous_session = restore_previous_session(chat_session_configs)

  if previous_session:
    return GptChat(previous_session, chat_session_configs)
  else:
    return GptChat(get_new_session(chat_session_configs), chat_session_configs)


def get_gpt_chat_configs() -> GptChatSessionConfigs:
  return GptChatSessionConfigs(config_collection.max_messages_per_request.get_int_value(),
                               config_collection.snippet_header_background_color.get_value(),
                               config_collection.snippet_theme.get_value())


def restore_previous_session(configs: GptChatSessionConfigs) -> Optional[GptChatSession]:
  always_continue_last_session = config_collection.always_continue_last_session.get_bool_value()
  active_session = get_active_session()

  if always_continue_last_session and active_session:
    return GptChatSession.from_session_id(active_session.session_id, configs)

  if active_session:
    old_session_cutoff_time_in_seconds = config_collection.inactive_session_cutoff_time_in_seconds.get_int_value()
    is_active_session_expired = int(
      time.time()) - old_session_cutoff_time_in_seconds > active_session.last_active_time

    if not is_active_session_expired:
      return GptChatSession.from_session_id(active_session.session_id, configs)

  return None


def get_new_session(session_configs: GptChatSessionConfigs) -> Optional[GptChatSession]:
  session = GptChatSession.create_new(session_configs)
  set_active_session_id(session.session_id)
  return session


def print_session_preview_message(session: GptChatSession):
  if session.turns:
    session_preview = get_preview_for_session(session.session_id)
    if session_preview:
      print(f'Continuing from session: {session_preview.session_preview}')
  else:
    print('Started new session')
