# ChatGPT CLI Client

## Installation

### Manual Installation

    git clone https://github.com/hansololz/rubberduck-ai.git
    cd rubberduck-ai
    python setup.py install

### Installation (pip)

    pip install rubberduck-ai

## Authentication

### Authentication Token
The CLI tool requires Open AI authentication token. Token can be obtained 
by going to https://platform.openai.com/account/api-keys.

### Authentication Methods
Choose one of these options to authenticate the CLI tool:
- Set the environment variable: `OPENAI_API_KEY=<AUTHENTICATION_TOKEN>`.
- Use a command argument: `rda --openai-api-key=<AUTHENTICATION_TOKEN>`.
- Enter the API key when prompted while running the CLI tool.

## Usage

### Evaluation Loop
Run the application:
    
    rda

#### Supported Commands
- .n .new: Create new session
- .p .print: Print current session 
- .s .sessions: Change chat session
- cd clear ls: Session supported bash commands
- cd cls dir: Session supported cmd commands

### Single Prompt
Process a single prompt with:

    rda <SINGLE_PROMPT> --openai-api-key=<AUTHENTICATION_TOKEN>
