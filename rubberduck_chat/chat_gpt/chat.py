import re

import inquirer
import openai
import pyperclip
from halo import Halo
from rich.console import Console
from rich.syntax import Syntax

from rubberduck_chat.chat_gpt.session_store import *
from rubberduck_chat.utils import get_datetime
from dataclasses import dataclass


@dataclass
class GptChatSessionConfigs:
  max_messages_per_request: int
  snippet_header_background_color: str
  snippet_theme: str


class GptChatSession:
  snippet_end_pattern = r'\s*```'
  snippet_start_pattern = r'\s*```(\S+)?'
  quote_pattern = re.compile(r'`([^`]*)`')

  def __init__(self, session_id, configs: GptChatSessionConfigs, session_metadata: GptSessionMetadata,
               system_message: GptSystemMessage,
               turns: List[GptChatTurn]):

    self.session_id: str = session_id
    self.configs: GptChatSessionConfigs = configs
    self.session_metadata: GptSessionMetadata = session_metadata
    self.system_message: GptSystemMessage = system_message
    self.turns: List[GptChatTurn] = turns
    self.console: Console = Console()
    self.snippets: List[str] = []

  @classmethod
  def create_new(cls, configs: GptChatSessionConfigs):
    message = GptSystemMessage.from_system_message('You are a helpful assistant')
    session_id = str(uuid4())
    return cls(session_id, configs, GptSessionMetadata(session_id, int(time.time())), message, [])

  @classmethod
  def from_session_id(cls, session_id: str, configs: GptChatSessionConfigs):
    lines: List[str] = fetch_session_data(session_id)

    gpt_session_metadata: GptSessionMetadata = GptSessionMetadata.from_line(lines[0])
    gpt_system_message: GptSystemMessage = GptSystemMessage.from_json_string(lines[1])
    gpt_chat_turns: List[GptChatTurn] = []
    turn_ids: set[str] = set()

    for line in lines[-1:1:-1]:
      turn = GptChatTurn.from_json_string(line)

      if turn.id in turn_ids:
        continue

      turn_ids.add(turn.id)
      gpt_chat_turns.append(turn)

    gpt_chat_turns.reverse()

    return cls(session_id, configs, gpt_session_metadata, gpt_system_message, gpt_chat_turns)

  def print_current_session(self, print_time=False):
    for turn in self.turns:
      if print_time:
        create_time = f'[{get_datetime(turn.created_time)}] '
      else:
        create_time = ''

      print(f'>>>{create_time}{turn.user_prompt}')
      assistant_response = turn.get_assistant_response()
      if assistant_response:
        self.print_assistant_response(assistant_response)

  def process_prompt(self, prompt: str):
    current_turn = GptChatTurn.from_user_prompt(prompt)
    self.store_chat_turn(current_turn)
    self.turns.append(current_turn)
    messages: List[dict] = [self.system_message.get_chat_gpt_request_message()]

    for turn in self.turns[-(self.configs.max_messages_per_request + 1):]:
      messages.append(turn.get_user_prompt_message())
      assistant_response_message = turn.get_assistant_response_message()
      if assistant_response_message:
        messages.append(assistant_response_message)

    response = None
    error_message = None

    with Halo(text='Fetching', spinner='dots'):
      try:
        response = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages)
      except Exception as error:
        error_message = str(error)

    if error_message:
      print(error_message)
      return

    if response:
      current_turn.updated_response(response)
      self.store_chat_turn(current_turn)
      self.print_assistant_response(current_turn.get_assistant_response())
    else:
      print('No results found')

  def print_assistant_response(self, message: str):
    new_snippets: List[str] = []
    message_parts = message.split('\n')

    snippet = None
    snippet_language = None
    snippet_count = 0

    for part in message_parts:
      if re.search(self.snippet_end_pattern, part) and snippet is not None:
        self.print_header(snippet_language, snippet_count)
        self.print_code(snippet_language, snippet)
        new_snippets.append(snippet)
        snippet = None
        snippet_language = None
      elif re.search(self.snippet_start_pattern, part):
        matches = re.findall(self.snippet_start_pattern, part)
        if matches:
          snippet_language = matches[0]
        else:
          snippet_language = None
        snippet = ''
        snippet_count += 1
      elif snippet is not None:
        snippet += part + '\n'
      elif not part:
        print()
      else:
        self.print_text(part)

    if new_snippets:
      self.snippets = new_snippets

    print('')

  def print_header(self, language: str, count: int):
    copy_message = f'Enter "{count}" to copy snippet'

    if language:
      header = f' {language.upper()} | {copy_message}'
    else:
      header = f' {copy_message}'

    syntax = Syntax(header, 'text', theme=self.configs.snippet_theme,
                    background_color=self.configs.snippet_header_background_color)
    self.console.print(syntax, overflow='fold')

  def print_code(self, language: str, code: str):
    if not language:
      language = 'text'

    syntax = Syntax(code, language, theme=self.configs.snippet_theme)
    self.console.print(syntax, overflow='fold')

  def print_text(self, text: str):
    highlighted_text = self.quote_pattern.sub(r'`\033[1m\1\033[0m`', text)
    print(highlighted_text)

  def has_snippet(self, snippet_index: int) -> bool:
    return snippet_index <= len(self.snippets)

  def copy_snippet(self, snippet_index: int):
    if snippet_index <= len(self.snippets):
      pyperclip.copy(self.snippets[snippet_index - 1])
      print('Snippet copied to clipboard')
    else:
      print('No snippet to copy')

  def store_chat_turn(self, gpt_chat_turn: GptChatTurn):
    if self.turns:
      store_chat_turn_to_file(self.session_id, gpt_chat_turn)
    else:
      store_metadata_to_file(self.session_id, self.session_metadata)
      store_system_message_to_file(self.session_id, self.system_message)
      store_chat_turn_to_file(self.session_id, gpt_chat_turn)


class GptChat:

  def __init__(self, session: GptChatSession, configs: GptChatSessionConfigs):
    self.session = session
    self.configs = configs

  def process_prompt(self, prompt: str):
    self.session.process_prompt(prompt)

  def create_new_session(self):
    self.session = GptChatSession.create_new(self.configs)
    set_active_session_id(self.session.session_id)
    print('Started new session')

  def update_configs(self, configs: GptChatSessionConfigs):
    self.configs = configs
    self.session.configs = configs

  def has_snippet(self, snippet_index: int) -> bool:
    return self.session.has_snippet(snippet_index)

  def copy_snippet(self, snippet_index: int):
    self.session.copy_snippet(snippet_index)

  def print_current_session(self):
    self.session.print_current_session(print_time=True)

  def change_session(self):
    session_previews = get_all_session_previews()

    if not session_previews:
      print('No previous session found')
      return

    message = f'Select from {len(session_previews)} sessions'

    previews = []

    for session_preview in session_previews:
      previews.append((session_preview.session_preview, session_preview))

    options = [inquirer.List('option', message=message, choices=previews)]
    answers = inquirer.prompt(options)

    if answers:
      preview: GptSessionPreview = answers['option']
      self.session = GptChatSession.from_session_id(preview.session_id, self.configs)
      self.session.print_current_session(print_time=True)
      set_active_session_id(preview.session_id)
      print(f'Loaded session: {preview.session_preview}')
