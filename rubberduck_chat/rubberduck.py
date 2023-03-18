import argparse

from rubberduck_chat.chat_gpt.setup_gpt import setup_gpt, print_session_preview_message
from rubberduck_chat.configs import setup_default_config
from rubberduck_chat.input_handler import start_evaluation_loop, print_get_help_message, print_hello_message
from rubberduck_chat.store import setup_rubberduck_dir

parser = argparse.ArgumentParser(description='Rubberduck AI')
parser.add_argument('single_prompt', nargs='?', default=None, help='Single prompt for the chat session.')
parser.add_argument('--openai-api-key', required=False, help='OpenAI API key.')
args = parser.parse_args()


def main():
  setup_rubberduck_dir()
  setup_default_config()

  gpt_chat = setup_gpt(args.openai_api_key)

  if args.single_prompt:
    gpt_chat.process_prompt(args.single_prompt)
  else:
    print_hello_message()
    print_get_help_message()
    print_session_preview_message(gpt_chat.session)
    start_evaluation_loop(gpt_chat)


if __name__ == '__main__':
  main()
