import configparser
import os
import platform
from dataclasses import dataclass

from rubberduck_chat.store import rubberduck_dir_name

configs_filename = 'configs.ini'
default_config_section_name = 'default'
config_array_delimiter = ','

configs = configparser.ConfigParser()


@dataclass
class ConfigEntry:
  name: str
  default_value: str
  description: str = ''

  def get_value(self):
    return configs[default_config_section_name][self.name]


@dataclass
class ConfigSet:
  max_saved_session_count = ConfigEntry(
    'max_saved_session_count',
    str(100),
    'Maximum number of sessions saved locally'
  )
  always_continue_last_session = ConfigEntry(
    'always_continue_last_session',
    str(False),
    'Always continue from your previous session'
  )
  inactive_session_cutoff_time_in_seconds = ConfigEntry(
    'inactive_session_cutoff_time_in_seconds',
    str(10800),
    'Continue from the previous session if you recently interacted with the previous session'
  )
  supported_command_cli = ConfigEntry(
    'supported_command_cli',
    config_array_delimiter.join(['clear', 'ls', 'cd'] if platform.system() == 'Windows' else ['cls', 'dir', 'cd']),
    ''
  )
  exit_command_trigger = ConfigEntry(
    'exit_command_trigger',
    config_array_delimiter.join(['.exit', '.e']),
    ''
  )
  help_command_trigger = ConfigEntry(
    'help_command_trigger',
    config_array_delimiter.join(['.help', '.h']),
    ''
  )
  change_session_command_trigger = ConfigEntry(
    'change_session_command_trigger',
    config_array_delimiter.join(['.sessions', '.s']),
    ''
  )
  print_session_command_trigger = ConfigEntry(
    'print_session_command_trigger',
    config_array_delimiter.join(['.print', '.p']),
    ''
  )
  new_session_command_trigger = ConfigEntry(
    'new_session_command_trigger',
    config_array_delimiter.join(['.new', '.n']),
    ''
  )
  update_key_command_trigger = ConfigEntry(
    'update_key_command_trigger',
    config_array_delimiter.join(['.key', '.k']),
    ''
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
