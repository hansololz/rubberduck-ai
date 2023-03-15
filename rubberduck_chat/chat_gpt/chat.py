import re

import inquirer
import openai
import pyperclip
from halo import Halo
from rich.console import Console
from rich.syntax import Syntax

from rubberduck_chat.chat_gpt.credentials import get_openai_api_key
from rubberduck_chat.chat_gpt.session_store import *
from rubberduck_chat.utils import get_datetime
from rubberduck_chat.configs import config_collection


def get_message_from_response(response) -> Optional[str]:
  choices = response['choices']

  if not choices:
    return None

  choice = choices[0]
  message = choice['message']['content']
  return message


class GptChatSession:
  snippet_end_pattern = r'\s*```'
  snippet_start_pattern = r'\s*```(\S+)?'
  quote_pattern = re.compile(r'`([^`]*)`')

  def __init__(self, session_filename, session_metadata: GptSessionMetadata, system_message: GptSystemMessage,
               turns: list[GptChatTurn]):
    self.session_filename: Optional[str] = session_filename
    self.session_metadata = session_metadata
    self.system_message = system_message
    self.turns: list[GptChatTurn] = turns
    self.prompt_to_remember = 10
    self.console = Console()
    self.snippets: list[str] = []

  @classmethod
  def create_new(cls):
    message = GptSystemMessage.from_system_message('You are a helpful assistant')
    return cls(None, GptSessionMetadata(int(time.time())), message, [])

  @classmethod
  def from_session_filename(cls, session_filename):
    lines = fetch_session_data(session_filename)

    gpt_session_metadata = GptSessionMetadata.from_line(lines[0])
    gpt_system_message = GptSystemMessage(GptMessage.from_line(lines[1]))
    gpt_chat_turns: list[GptChatTurn] = []

    current_turn: Optional[GptChatTurn] = None

    for line_index in range(2, len(lines)):
      message = GptMessage.from_line(lines[line_index])

      if current_turn:
        if message.role == GptRole.ASSISTANT:
          current_turn.updated_assistant_response_with_message(message)
          current_turn = None
        if message.role == GptRole.USER:
          current_turn = GptChatTurn(message, None)
          gpt_chat_turns.append(current_turn)
      else:
        if message.role == GptRole.USER:
          current_turn = GptChatTurn(message, None)
          gpt_chat_turns.append(current_turn)

    return cls(session_filename, gpt_session_metadata, gpt_system_message, gpt_chat_turns)

  def print_current_session(self, print_date=False):
    for turn in self.turns:
      if print_date:
        create_time = f' [{get_datetime(turn.user_prompt.created_time)}]'
      else:
        create_time = ''

      print(f'>>>{create_time} {turn.user_prompt.content}')
      if turn.assistant_response:
        self.print_assistant_response(turn.assistant_response.content)

  def process_prompt(self, prompt: str):
    current_turn = GptChatTurn.from_user_prompt(prompt)
    self.store_user_prompt(current_turn)
    self.turns.append(current_turn)
    messages = [self.system_message.system_message.get_message()]

    for turn in self.turns[-self.prompt_to_remember:]:
      user_prompt = turn.user_prompt.get_message()
      messages.append(user_prompt)
      if turn.assistant_response:
        messages.append(turn.assistant_response.get_message())

    with Halo(text='Fetching', spinner='dots'):
      try:
        response = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=messages)
        message = get_message_from_response(response)
      except Exception as error:
        print(error)

    if message:
      current_turn.updated_assistant_response(message)
      self.store_assistant_message(current_turn)
      self.print_assistant_response(message)
    else:
      print('No results found')

  def print_assistant_response(self, message: str):
    new_snippets: list[str] = []
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
    copy_message = f'Press "{count}" to copy snippet'

    if language:
      header = f' {language.upper()} | {copy_message}'
    else:
      header = f' {copy_message}'

    syntax = Syntax(header, 'text', theme='monokai', background_color='#808080')
    self.console.print(syntax, overflow='fold')

  def print_code(self, language: str, code: str):
    if not language:
      language = 'text'

    syntax = Syntax(code, language, theme='monokai')
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

  def store_user_prompt(self, gpt_chat_turn: GptChatTurn):
    if not self.session_filename:
      self.session_filename = create_session_filename()

    set_active_session_filename(self.session_filename)

    if self.turns:
      store_message_to_file(self.session_filename, gpt_chat_turn.user_prompt)
    else:
      store_metadata_to_file(self.session_filename, self.session_metadata)
      store_message_to_file(self.session_filename, self.system_message.system_message)
      store_message_to_file(self.session_filename, gpt_chat_turn.user_prompt)

  def store_assistant_message(self, gpt_chat_turn: GptChatTurn):
    store_message_to_file(self.session_filename, gpt_chat_turn.assistant_response)


class GptChat:

  def __init__(self):
    self.session = None
    openai.api_key = get_openai_api_key()

    def start_new_session():
      self.session = GptChatSession.create_new()
      unset_active_session()
      print('Started new session')

    def continue_from_session(session_filename: str):
      self.session = GptChatSession.from_session_filename(session_filename)
      session_preview = get_preview_from_session_file(session_filename)
      if session_preview:
        print(f'Continuing from session: {session_preview.session_preview}')

    always_continue_last_session = config_collection.always_continue_last_session.get_value() == 'True'

    if always_continue_last_session:
      active_session = get_active_session()

      if active_session:
        continue_from_session(active_session.filename)
        return

    active_session = get_active_session()

    if not active_session:
      start_new_session()
      return

    old_session_cutoff_time_in_seconds = int(config_collection.inactive_session_cutoff_time_in_seconds.get_value())

    if int(time.time()) - old_session_cutoff_time_in_seconds > active_session.last_active_time:
      start_new_session()
      return

    continue_from_session(active_session.filename)

  def process_prompt(self, prompt: str):
    self.session.process_prompt(prompt)

  def create_new_session(self):
    self.session = GptChatSession.create_new()
    unset_active_session()
    print('Started new session')

  def has_snippet(self, snippet_index: int) -> bool:
    return self.session.has_snippet(snippet_index)

  def copy_snippet(self, snippet_index: int):
    self.session.copy_snippet(snippet_index)

  def print_current_session(self):
    self.session.print_current_session(print_date=True)

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
      self.session = GptChatSession.from_session_filename(preview.session_filename)
      self.session.print_current_session(print_date=True)
      set_active_session_filename(preview.session_filename)
      print(f'Loaded session: {preview.session_preview}')
