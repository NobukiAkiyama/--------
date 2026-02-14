# Goose Coding Assistant Integration

## Overview
Square's Goose AI coding assistant is integrated as a tool for handling coding tasks only.

## Installation

### 1. Install Goose CLI
```powershell
# Using pipx (recommended)
pip install pipx
pipx install goose-ai

# Verify installation
goose --version
```

### 2. Install Python Package (already in requirements.txt)
```powershell
pip install goose-ai>=0.9.0
```

## Usage

### Via Router
The AI can automatically invoke Goose for coding tasks:
```json
{
  "tool": "goose_code",
  "params": {
    "task": "Create a Python function that calculates fibonacci numbers",
    "workspace": "c:/Users/nobuk/Desktop/新しいフォルダー",
    "files": ["src/utils.py"]
  }
}
```

### Parameters
- `task` (required): Description of the coding task
- `workspace` (optional): Directory to execute in (default: current directory)
- `files` (optional): List of file paths to include in context

### Example Tasks
- "Refactor this function to be more efficient"
- "Add type hints to all functions in utils.py"
- "Create unit tests for the DatabaseManager class"
- "Fix the bug in discord_bot.py where users aren't being registered"

## Integration with Rito AI

The Router will use `goose_code` when:
- コーディングタスクが必要な時
- リファクタリングが必要な時
- バグ修正が必要な時

## Limitations
- **Coding only**: Goose is restricted to coding tasks (no SNS posting, vision, etc.)
- **Subprocess execution**: Runs as external CLI tool (5-minute timeout)
- **Requires installation**: Must install Goose CLI separately via pipx

## Troubleshooting

### "Goose CLI not found"
Install via: `pipx install goose-ai`

### Timeout errors
Increase timeout in `src/adapter/goose.py` (default: 300 seconds)
