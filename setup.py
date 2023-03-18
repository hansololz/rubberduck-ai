from setuptools import find_packages, setup

from rubberduck_chat import __version__

with open('requirements.txt') as f:
  requirements = [line for line in f.read().splitlines() if line]

setup(
  name='rubberduck-ai',
  version=__version__,
  description='A CLI tool for ChatGPT.',
  url='https://github.com/hansololz/rubberduck-ai',

  keywords=["rda", 'openai', 'ChatGPT', 'chat'],
  packages=find_packages(),
  include_package_data=True,

  install_requires=requirements,
  entry_points={
    'console_scripts': [
      'rda = rubberduck_chat.rubberduck:main',
    ]
  },
  license='CCPL',
)
