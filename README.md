# Minesweeper Telegram Bot

A Telegram bot that implements the classic Minesweeper game using Inline Keyboard buttons. Deployed on Render using Polling for Telegram API interaction.

## Features
- Play Minesweeper on an 8x8 grid with 10 mines.
- Inline buttons for interactive gameplay.
- Commands:
  - `/start`: Start a new game.
  - `/help`: Display game instructions.

## Setup
1. Create a Telegram bot using `@BotFather` and obtain a bot token.
2. Add the bot token as an environment variable `BOT_TOKEN` on Render.
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
