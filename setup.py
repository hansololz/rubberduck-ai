import atexit

from setuptools import find_packages, setup

from rubberduck_chat import __version__


def print_message():
  print('Type `rda` in the CLI to start chat session.')


atexit.register(print_message)

with open('requirements.txt') as f:
  requirements = [line for line in f.read().splitlines() if line]

with open("README.md", "r") as fh:
  long_description = fh.read()

setup(
  name='rubberduck-ai',
  version=__version__,
  description='A CLI tool for ChatGPT.',
  long_description=long_description,
  long_description_content_type="text/markdown",
  url='https://github.com/hansololz/rubberduck-ai',

  keywords=["rda", 'openai', 'ChatGPT', 'chat'],
  packages=find_packages(),
  include_package_data=True,

  python_requires='>=3.5',
  install_requires=requirements,
  entry_points={
    'console_scripts': [
      'rda = rubberduck_chat.rubberduck:main',
    ]
  },
  license='GPL',
)
