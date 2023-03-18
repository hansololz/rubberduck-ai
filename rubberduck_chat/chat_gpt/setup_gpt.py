import os
from typing import Optional

from rubberduck_chat.chat_gpt.chat import GptChat
from rubberduck_chat.chat_gpt.credentials import setup_gpt_credentials
from rubberduck_chat.chat_gpt.session_store import get_gpt_dir_path, get_gpt_session_dir_path, \
  create_get_gpt_session_dir, remove_old_sessions
from rubberduck_chat.configs import config_collection


def setup_gpt(openai_api_key: Optional[str]) -> GptChat:
  max_saved_session_count = int(config_collection.max_saved_session_count.get_value())

  os.makedirs(get_gpt_dir_path(), exist_ok=True)
  os.makedirs(get_gpt_session_dir_path(), exist_ok=True)

  setup_gpt_credentials(openai_api_key)
  create_get_gpt_session_dir()
  remove_old_sessions(max_saved_session_count)

  return GptChat()
