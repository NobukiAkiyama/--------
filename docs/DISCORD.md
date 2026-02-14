# Discord Bot Setup

## Prerequisites

1. Create a Discord Bot at https://discord.com/developers/applications
2. Enable the following intents:
   - Message Content Intent
   - Server Members Intent
3. Copy the Bot Token

## Configuration

Add to `.env`:
```
DISCORD_BOT_TOKEN=your_bot_token_here
```

## Running the Bot

```powershell

python -m src.adapter.discord_bot
```

## Features

- **Multi-User Support**: Automatically tracks each Discord user
- **Relationship Tracking**: Adjusts intimacy based on interactions
- **Memory**: Remembers past conversations per user
- **Context-Aware**: Uses user history to generate personalized responses

## User Management

Users are automatically registered on first message. You can manage them via:
- Dashboard → Relationship Manager
- Direct database edits

## Commands

Currently responds to all messages. Prefix commands (e.g., `!help`) coming soon.
