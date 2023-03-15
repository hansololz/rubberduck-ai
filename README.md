ChatGPT command-line client
===========================

Work in progress, still trying polish a few features and getting some initial feedback,.

Installation
------------

To install manually

    git clone https://github.com/hansololz/rubberduck-ai.git
    cd rubberduck-ai
    python3 setup.py install

I'll publish this a pip module for this in a bit in the future.

Authentication Token
--------------------

The CLI tool requires Open AI authentication token. Token can be obtained 
by going to https://platform.openai.com/account/api-keys. To authenticate
the CLI tool, set the environment variable 
`OPENAI_API_KEY=<AUTHENTICATION_TOKEN>`.

Usage
-----
Start the application by typing `rda` in the command line.

### Supported Commands
- .n .new: Create new session
- .p .print: Print current session 
- .s .sessions: Change chat session
- cd clear ls: Input is executed on the command line