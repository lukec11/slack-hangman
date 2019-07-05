# Slack Hangman Bot

This is a work-in-progress hangman bot for Slack.

To get started, clone the repository and copy `config.json.template` to `config.json`.
Update the value of `slack_token` to be your Slack app's "Bot User OAuth Access Token".

Install dependencies and run the bot:

```bash
pip3 install slackclient
python3 hangman_bot.py
```

If you use Windows, use
```
py -m pip install slackclient
python3 hangman_bot.py
```

## How to use it

To use the bot, DM the bot in this format:
`phrase attempts`

So if your phrase was `play hangman` and you wanted there to be 14 attempts, you would DM (without the code formatting)

`play hangman 14`

Then, the bot will use the delegated channel (set channel in the code) to start the game. To play the game, reply to the new game that the bot has posted.
