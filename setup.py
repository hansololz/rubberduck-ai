from rubberduck_chat import __version__
from setuptools import find_packages, setup

with open('requirements.txt') as f:
  requirements = [l for l in f.read().splitlines() if l]

with open("README.md") as readme_file:
  readme = readme_file.read()

setup(
  name='rubberduck-ai',
  version=__version__,
  description='A CLI tool for ChatGPT.',
  long_description=readme,

  keywords=["rda", 'openai', 'ChatGPT', 'chat'],
  packages=find_packages(),
  include_package_data=True,

  install_requires=requirements,
  entry_points={
    'console_scripts': [
      'rda = rubberduck_chat.rubberduck:main',
    ]
  },
  license='MIT',
)
