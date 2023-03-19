import configparser
import os
import platform
import re
from dataclasses import dataclass
from typing import Optional, List

import inquirer

from rubberduck_chat.store import rubberduck_dir_name

configs_filename = 'configs.ini'
default_config_section_name = 'default'
config_array_delimiter = ','

configs = configparser.ConfigParser()


def is_valid_int(value: str) -> bool:
  if value.isdigit() and int(value) >= 0:
    return True
  else:
    return False


def is_valid_bool(value: str) -> bool:
  return value.lower() in ['true', 'false']


def is_valid_color_code(value: str) -> bool:
  regex = r'^#?([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
  return re.match(regex, value) is not None


@dataclass
class ConfigEntry:
  name: str
  default_value: str
  description: str
  value_varifier: Optional[callable]

  def get_value(self) -> str:
    return configs[default_config_section_name][self.name]

  def set_value(self, value):
    configs[default_config_section_name][self.name] = value
    with open(get_configs_path(), 'w') as configfile:
      configs.write(configfile)

  def get_int_value(self) -> int:
    try:
      value = int(self.get_value())
      if value >= 0:
        return value
      else:
        return int(self.default_value)
    except ValueError:
      return int(self.default_value)

  def get_bool_value(self) -> bool:
    return self.get_value().lower() == 'true'


@dataclass
class ConfigSet:
  max_saved_session_count = ConfigEntry(
    'max_saved_session_count',
    str(100),
    'Maximum number of sessions saved locally',
    is_valid_int
  )
  always_continue_last_session = ConfigEntry(
    'always_continue_last_session',
    'false',
    'Always continue from your previous session',
    is_valid_bool
  )
  inactive_session_cutoff_time_in_seconds = ConfigEntry(
    'inactive_session_cutoff_time_in_seconds',
    str(172800),
    'Creat new session if previous session is inactive for this many seconds',
    is_valid_int
  )
  max_messages_per_request = ConfigEntry(
    'max_messages_per_request',
    str(10),
    'Maximum number of previous chat user prompts used to generating new responses',
    is_valid_int
  )
  snippet_header_background_color = ConfigEntry(
    'snippet_header_background_color',
    '#707070',
    'Snippet header background color',
    is_valid_color_code
  )
  snippet_theme = ConfigEntry(
    'snippet_theme',
    'monokai',
    'Snippet theme',
    None
  )
  exit_command_trigger = ConfigEntry(
    'exit_command_trigger',
    config_array_delimiter.join(['.exit', '.e']),
    'Commands to exit session',
    None
  )
  help_command_trigger = ConfigEntry(
    'help_command_trigger',
    config_array_delimiter.join(['.help', '.h']),
    'Commands to print help message',
    None
  )
  change_session_command_trigger = ConfigEntry(
    'change_session_command_trigger',
    config_array_delimiter.join(['.sessions', '.s']),
    'Commands to change current session',
    None
  )
  print_session_command_trigger = ConfigEntry(
    'print_session_command_trigger',
    config_array_delimiter.join(['.print', '.p']),
    'Commands to print current session',
    None
  )
  new_session_command_trigger = ConfigEntry(
    'new_session_command_trigger',
    config_array_delimiter.join(['.new', '.n']),
    'Commands to start new session',
    None
  )
  update_key_command_trigger = ConfigEntry(
    'update_key_command_trigger',
    config_array_delimiter.join(['.key', '.k']),
    'Commands to update openai API key',
    None
  )
  update_config_command_trigger = ConfigEntry(
    'update_config_command_trigger',
    config_array_delimiter.join(['.config', '.c']),
    'Commands to change configs',
    None
  )
  supported_command_cli = ConfigEntry(
    'supported_command_cli',
    config_array_delimiter.join(['cls', 'dir', 'cd'] if platform.system() == 'Windows' else ['clear', 'ls', 'cd']),
    'CLI commands supported by the chat',
    None
  )


config_collection = ConfigSet()
config_collection_list: List[ConfigEntry] = [
  config_collection.max_saved_session_count,
  config_collection.always_continue_last_session,
  config_collection.inactive_session_cutoff_time_in_seconds,
  config_collection.max_messages_per_request,
  config_collection.snippet_header_background_color,
  config_collection.snippet_theme,
  config_collection.exit_command_trigger,
  config_collection.help_command_trigger,
  config_collection.change_session_command_trigger,
  config_collection.print_session_command_trigger,
  config_collection.new_session_command_trigger,
  config_collection.update_key_command_trigger,
  config_collection.update_config_command_trigger,
  config_collection.supported_command_cli,
]


def get_configs_path() -> str:
  return os.path.join(os.path.expanduser('~'), rubberduck_dir_name, configs_filename)


def setup_default_config(override_existing_configs: bool = False):
  config_filepath = get_configs_path()
  configs.read(get_configs_path())

  if default_config_section_name not in configs:
    configs.add_section(default_config_section_name)

  for config in config_collection_list:
    if override_existing_configs or config.name not in configs[default_config_section_name]:
      configs[default_config_section_name][config.name] = config.default_value

  with open(config_filepath, 'w') as configfile:
    configs.write(configfile)


def update_config():
  options: List[tuple[str, ConfigEntry]] = [
    ('Reset all configs', ConfigEntry('reset_all', '', '', None))
  ]

  for config in config_collection_list:
    description = f'{config.description}: {config.get_value()}'
    options.append((description, config))

  print('Select a config to update, press Ctrl+C to exit.')
  answers = inquirer.prompt([inquirer.List('config', message='Selected', choices=options)])

  if answers:
    config = answers["config"]

    if config.name == 'reset_all':
      setup_default_config(override_existing_configs=True)
      print('Config reset to default.')
    else:
      while True:
        questions = [
          inquirer.Text("new_value", message=f"New value", default=config.get_value())
        ]

        result = inquirer.prompt(questions)

        if not result:
          break

        new_value = result['new_value']

        if new_value:
          if not config.value_varifier:
            config.set_value(new_value)
            print(f'Config updated with value: {new_value}')
            break
          elif config.value_varifier:
            if config.value_varifier(new_value):
              config.set_value(new_value)
              print(f'Config updated with value: {new_value}')
              break
            else:
              print('Invalid value, please try again.')
        else:
          break
