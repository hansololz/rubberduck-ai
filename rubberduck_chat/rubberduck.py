import argparse

from rubberduck_chat.chat_gpt.setup_gpt import setup_gpt, print_session_preview_message
from rubberduck_chat.configs import setup_default_config
from rubberduck_chat.input_handler import start_evaluation_loop, print_get_help_message, print_hello_message
from rubberduck_chat.store import setup_rubberduck_dir

parser = argparse.ArgumentParser(description='Rubberduck AI')
parser.add_argument('single_prompt', nargs='?', default=None, help='Single prompt for the chat session.')
parser.add_argument('-k', '--openai-api-key', default=None, required=False, help='OpenAI API key.')
parser.add_argument('-p', '--print-session', action='store_true', required=False, help='Print current session.')
parser.add_argument('-v', '--version', action='store_true', required=False, help='Print version.')
args = parser.parse_args()


def main():

  if args.version:
    from rubberduck_chat import __version__
    print(f'v{__version__}')
    return

  setup_rubberduck_dir()
  setup_default_config()

  gpt_chat = setup_gpt(args.openai_api_key)

  if args.print_session:
    gpt_chat.print_current_session()
  elif args.single_prompt:
    gpt_chat.process_prompt(args.single_prompt)
  else:
    print_hello_message()
    print_get_help_message()
    print_session_preview_message(gpt_chat.session)
    start_evaluation_loop(gpt_chat)


if __name__ == '__main__':
  main()
