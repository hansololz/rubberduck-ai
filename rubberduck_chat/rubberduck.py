from rubberduck_chat.chat_gpt.setup_gpt import setup_gpt
from rubberduck_chat.configs import setup_default_config
from rubberduck_chat.input_handler import start_evaluation_loop, print_get_help_message
from rubberduck_chat.store import setup_rubberduck_dir
import argparse


parser = argparse.ArgumentParser(description='Rubberduck AI')
parser.add_argument('--openai-api-key', required=False, help='OpenAI API key.')
args = parser.parse_args()


def main():
  print('Welcome to Rubberduck AI v0.1')
  setup_rubberduck_dir()
  setup_default_config()

  print_get_help_message()
  gpt_chat = setup_gpt(args.openai_api_key)
  start_evaluation_loop(gpt_chat)


if __name__ == '__main__':
  main()
