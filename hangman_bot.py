#!/usr/bin/python3

import os
import time
import re
import slack
import copy
import json
from cloudant.client import CouchDB
from game import Game

BOT_ID = ""
games = {}
channel = "#hangman"  # Put your channel here

enable_banker_support = True
banker_id = "<@banker>"

config = os.environ
couch_user = config.get("couch_user")
couch_password = config.get('couch_password')
couch_url = config.get('couch_url')
couch_dbname = config.get("couch_dbname")

client = CouchDB(
    couch_user,
    couch_password,
    url=couch_url,
    connect=True,
    auto_renew=True
)

game_db = client[couch_dbname]
game_creation_sessions = {}  # Creation sessions
print("Slack Hangman Bot\nStarting up...\n")


@slack.RTMClient.run_on(event="message")
def message_on(**payload):
    # To make sure the bot doesn't reply to its messages in a thread.
    global BOT_ID
    global channel
    global game_db

    mention = f"<@{BOT_ID}>"
    data = payload["data"]
    web_client = payload['web_client']
    rtm_client = payload['rtm_client']

    if BOT_ID == data.get('user'):
        return

    try:
        a = data['text']
    except UnicodeEncodeError:
        return
    except KeyError:
        return

    if data.get('user'):  # Debug to figure out if bot is responding to itself.
        print("Bot ID equals user ID?")
        print(BOT_ID == data.get('user'))

#        print("\nData is \n" + str(data))

    if data.get('text') and data.get('user'):

        if data.get('text').startswith(mention):
            # Bot got mentioned!
            web_client.chat_postMessage(
                channel=data.get('channel'),
                text=f":thinking_face: I don't think I quite understand. Try `!newgame` in a DM to start a game and if you want to cancel the game you're making try `!stopgame` :wink:",
            )

        if data.get('channel')[0] == "D":
            # Is a DM, start the interactive process of making a new game
            text = data.get('text')

            # Banker is DM'ing you about funding GP, ignore threads.
            if data.get('user') == "UH50T81A6":
                if data.get('thread_ts'):  # In thread, print and do nothing
                    print(text)
                    return

                transaction_raw = text.split("|")
                # Need this for potential refunds.
                user = transaction_raw[1].strip()
                reason = transaction_raw[3].strip()[5:].replace(
                    '"', "")  # Get reason aka thread
                amount = int(transaction_raw[2].strip())  # Get amount

                # Get game.
                fund_game = Game.from_db(reason)
                # Funded game. Correct amount of gp was provided.
                if fund_game.game['gp'] == amount:
                    # Game funded
                    fund_game.game['gp_funded'] = True
                    fund_game.game.save()
                    fund_game.post_funded()

                else:  # Refund the user, they didn't pay enough
                    web_client.chat_postMessage(
                        channel=data.get('channel'),
                        text=f"give {user} {amount} for Declined funding",
                        as_user=True
                    )

            if text == "!newgame":
                web_client.chat_postMessage(
                    channel=data.get('channel'),
                    text=f":heavy_check_mark: Let's get started! What's the word or phrase?"
                )

                # Add to session
                game_creation = {}
                game_creation_sessions[data.get('user')] = game_creation
                return
            if text == "!stopgame":
                # Delete the session and tell the user
                del game_creation_sessions[data.get('user')]

                web_client.chat_postMessage(
                    channel=data.get('channel'),
                    text=f"I've stopped the game you were creating."
                )

            if data.get('user') in game_creation_sessions:
                # User started a session
                session = game_creation_sessions.get(data.get('user'))
                if not session.get('word'):  # If no word in session, add that first
                    session['word'] = data.get('text')

                    # Save session
                    game_creation_sessions[data.get('user')] = session

                    web_client.chat_postMessage(
                        channel=data.get('channel'),
                        text=f":heavy_check_mark: Great! Now how many attempts should this game have (defaults to 10)?"
                    )

                elif not session.get('attempts'):  # Proceed to attempts
                    if data.get('text').isnumeric():
                        session['attempts'] = int(data.get('text'))
                    else:
                        session['attempts'] = 10

                    # Save session
                    game_creation_sessions[data.get('user')] = session

                    web_client.chat_postMessage(
                        channel=data.get('channel'),
                        text=f":heavy_check_mark: Should this game be case sensitive (yes/anything for no)?"
                    )
                elif session.get("case_sensitive") == None:  # Proceed to attempts
                    session['case_sensitive'] = True if data.get(
                        "text").lower() == "yes" else False
                    case_sens_str = "" if session['case_sensitive'] else "Case sensitivity is *disabled*. "

                    # Save session
                    game_creation_sessions[data.get('user')] = session

                    web_client.chat_postMessage(
                        channel=data.get('channel'),
                        text=f"{case_sens_str}Would you like to fund this game with gp (yes/anything for no)? "
                    )

                elif session.get("gp_userfunded") == None:  # Proceed to attempts
                    session['gp_userfunded'] = True if data.get(
                        'text') == "yes" else False
                    game_creation_sessions[data.get('user')] = session

                    if not session['gp_userfunded']:
                        # Create the game with 4 gp.
                        new_game = Game(
                            data.get('user'),
                            session['word'],
                            session['attempts'],
                            session['case_sensitive'],
                            4,
                            True  # This is to say the game is already paid for
                        )
                        new_game.start_game()

                        web_client.chat_postMessage(
                            channel=data.get('channel'),
                            text=f":thumbsup: The new game was started!"
                        )
                        del game_creation_sessions[data.get('user')]
                    elif session.get("gp_userfunded"):
                        # True, so we will do this process.
                        web_client.chat_postMessage(
                            channel=data.get('channel'),
                            text=f":thumbsup: How much gp do you want the game to be worth?"
                        )
                elif not session.get('gp'):
                    session['gp'] = int(data.get('text'))

                    # Create a game and get the ID
                    new_game = Game(
                        data.get('user'),
                        session['word'],
                        session['attempts'],
                        session['case_sensitive'],
                        session['gp'],
                        False  # Not funded!
                    )
                    new_game.start_game()

                    # Provide instructions on how to fund the game.
                    game_id = new_game.game["_id"]
                    web_client.chat_postMessage(
                        channel=data.get('channel'),
                        text=f":heavy_check_mark: All right. I've started the game. To fund the game, please type in \n```/give {mention} {session['gp']} for {game_id}```"
                    )

            else:  # Tell the user how to start a game.
                web_client.chat_postMessage(
                    channel=data.get('channel'),
                    text=f":thinking_face: I don't think I quite understand. Try `!newgame` to start a game and if you want to cancel the game you're making try `!stopgame` :wink:",
                    thread_ts=data.get('ts')
                )

    # For the actual game itself.
    if data.get('thread_ts') and (BOT_ID != data.get('user')):
        # Check if it's a game
        game = Game.from_db(data.get('thread_ts'))

        if game == None:  # Game doesn't exist.
            return

        # Check if game is deleted. If it is, do nothing.
        if len(game.game.keys()) == 1:
            return

        # Is a game, get guess
        guess = data.get('text').strip()

        # Handle !word
        if guess == "!word":
            game.display_word()

        # Handle regular guess
        # Make sure the bot isn't replying to itself.
        if data.get("user") != BOT_ID:
            game.guess(guess, data.get('user'))


slack_token = os.environ["slack_token"]

rtm_client = slack.RTMClient(token=slack_token)

client = slack.WebClient(token=slack_token)
BOT_ID = client.api_call("auth.test")["user_id"]


rtm_client.start()
