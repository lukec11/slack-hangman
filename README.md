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

