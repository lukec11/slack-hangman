# Slack Hangman Bot

This is a work-in-progress hangman bot for Slack.

## Setup

You need CouchDB for this bot. To install CouchDB, visit the CouchDB site and install CouchDB on your platform.
Once you've installed CouchDB, create a database and a user for use with this bot (you can access the CouchDB web UI to do this at http://localhost:5984)
if you installed CouchDB locally.

Now, let's set up the bot
* Clone the repository and copy `config.json.template` to `config.json`.
* Update the value of `slack_token` to be your Slack app's "Bot User OAuth Access Token".
* Update the `couch_user`, `couch_password`, `couch_url`, and `couch_dbname` to match what you created in CouchDB.
* If you are using Linux, you can deploy this bot easily with the systemd service. Copy `hangmanbot.service` to `/etc/systemd/system/` and edit the values of the user
to match your user.

Install dependencies:
```bash
pip3 install slackclient cloudant
```

If you use Windows, it might help to use
```
py -m pip install slackclient
```

## Running/Deploying

### Deploying with Linux

It is recommended on Linux, if you are not developing Hangman Bot to deploy using systemd. After following the setup instructions for the systemd service file, 
you may run 
```bash
systemctl daemon-reload
systemctl enable --now hangmanbot
```

### Running in a Development Environment
If wanting to normally run the program:

```
python3 hangman_bot.py
```


## How to use Hangman Bot

To use the bot, DM the bot in this format:
`phrase attempts`

So if your phrase was `play hangman` and you wanted there to be 14 attempts, you would DM (without the code formatting)

`play hangman 14`

Then, the bot will use the delegated channel (set channel in the code) to start the game. To play the game, reply to the new game that the bot has posted.
