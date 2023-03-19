import configparser
import os
import platform
from dataclasses import dataclass
from typing import Optional

import inquirer

from rubberduck_chat.store import rubberduck_dir_name

configs_filename = 'configs.ini'
default_config_section_name = 'default'
config_array_delimiter = ','

configs = configparser.ConfigParser()


def is_valid_int(value: str) -> bool:
  return value.isdigit()


def is_valid_bool(value: str) -> bool:
  return value.lower() in ['true', 'false']


@dataclass
class ConfigEntry:
  name: str
  default_value: str
  description: str
  value_varifier: Optional[callable]

  def get_value(self):
    return configs[default_config_section_name][self.name]

  def set_value(self, value):
    configs[default_config_section_name][self.name] = value
    with open(get_configs_path(), 'w') as configfile:
      configs.write(configfile)

  def get_int_value(self) -> int:
    try:
      return int(self.get_value())
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
  supported_command_cli = ConfigEntry(
    'supported_command_cli',
    config_array_delimiter.join(['cls', 'dir', 'cd'] if platform.system() == 'Windows' else ['clear', 'ls', 'cd']),
    'Supported CLI commands',
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


config_collection = ConfigSet()
config_collection_list: list[ConfigEntry] = [
  config_collection.max_saved_session_count,
  config_collection.always_continue_last_session,
  config_collection.inactive_session_cutoff_time_in_seconds,
  config_collection.supported_command_cli,
  config_collection.exit_command_trigger,
  config_collection.help_command_trigger,
  config_collection.change_session_command_trigger,
  config_collection.print_session_command_trigger,
  config_collection.new_session_command_trigger,
  config_collection.update_key_command_trigger,
  config_collection.update_config_command_trigger,
]


def get_configs_path() -> str:
  return os.path.join(os.path.expanduser('~'), rubberduck_dir_name, configs_filename)


def setup_default_config():
  config_filepath = get_configs_path()
  configs.read(get_configs_path())

  if default_config_section_name not in configs:
    configs.add_section(default_config_section_name)

  for config in config_collection_list:
    if config.name not in configs[default_config_section_name]:
      configs[default_config_section_name][config.name] = config.default_value

  with open(config_filepath, 'w') as configfile:
    configs.write(configfile)


def update_config():
  options: list[tuple[str, ConfigEntry]] = []

  for config in config_collection_list:
    description = f'{config.description}: {config.get_value()}'
    options.append((description, config))

  print('Select a config to update, press Ctrl+C to exit.')
  answers = inquirer.prompt([inquirer.List('config', message='Selected', choices=options)])

  if answers:
    config = answers["config"]

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
