import os
import time
import re
import slack
import copy
import json
from cloudant.client import CouchDB
import requests  # needed for new gp api

with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")) as cf:
    config = json.load(cf)
    slack_token = config.get('slack_token')
    couch_user = config.get("couch_user")
    couch_password = config.get('couch_password')
    couch_url = config.get('couch_url')
    couch_dbname = config.get("couch_dbname")
    channel_name = config.get('channel')
    banker_id = config.get('banker_id')
    banker_api = config.get('banker_api')
    banker_api_key = config.get('banker_api_key')
    bot_id = config.get('bot_id')

slack_client = slack.WebClient(token=slack_token)

client = CouchDB(
    couch_user,
    couch_password,
    url=couch_url,
    connect=True,
    auto_renew=True
)

game_db = client[couch_dbname]


class Game:
    def __init__(self, user, word, attempts, case_sensitive, gp, gp_userfunded):

        # Store everything in a dictionary because that makes everything easier for CouchDB.

        self.game = {}
        self.game['word'] = word if case_sensitive else word.lower()  # The word
        self.game['attempts'] = attempts  # Number of attempts
        # Whether the game is case sensitive
        self.game['case_sensitive'] = case_sensitive
        self.game['gp'] = gp  # Value of game in gp
        # Whether the game is being funded by a user
        self.game['gp_funded'] = gp_userfunded
        # The list of people who have played in the game.
        self.game['players'] = []
        self.game['user'] = user  # The user who made the game
        self.game['guesses'] = []  # List of letters that were already guessed.

        # Build the word template

        self.game['template'] = self._build_template(self.game['word'])

        # Get the slack client and channel name.

        global slack_client
        global channel_name
        global banker_api
        global banker_api_key
        global bot_id
        global requests

        self.slack_client = slack_client
        self.channel_name = channel_name
        self.banker_api = banker_api
        self.banker_api_key = banker_api_key
        self.bot_id = bot_id
        self.requests = requests

    @staticmethod
    def from_db(thread):
        """Inits a new game from a thread id/number"""
        global game_db
        r_game = Game("", "", 0, False, 0, False)

        if thread in game_db:
            r_game.game = game_db[thread]
        else:
            return None

        return r_game

    def start_game(self):
        """Posts game to designated channel"""
        global slack_client
        global channel_name

        # Get variables for readability

        user = self.game['user']
        template = self.game['template']
        case_sensitive_word = "" if self.game['case_sensitive'] else "not "
        attempts = self.game['attempts']
        gp = self.game['gp']

        # Build the message
        game_msg = f"<@{user}> has started a new game!\n"
        game_msg += f":point_right: The template is {template}\n"
        game_msg += f":point_right: There are {attempts} attempts\n"
        game_msg += f":point_right: The game is worth {gp} gp\n"
        # No space since the case_sensitive_word will have the space
        game_msg += f":point_right: The game is {case_sensitive_word}case sensitive\n"
        game_msg += f":thumbsup: To get started, reply with your guess in a new thread!"

        # If game not funded add a message about that
        if not self.game['gp_funded']:
            game_msg += f"\n*Note:* you'll have to wait for this game to be funded first."

        # We need the result of this to update the _id

        result = slack_client.chat_postMessage(
            channel=channel_name,
            text=game_msg,
            as_user=True
        )

        # This is the thread number or whatever it's called.
        self.game['_id'] = result['ts']

        # Save the game to CouchDB

        global game_db
        game_db.create_document(self.game)

        # Rewrite the dictionary with a CouchDB game.
        self.game = game_db.get(self.game['_id'])

    def post_funded(self):
        """Post that the game has been funded."""
        self.slack_client.chat_postMessage(
            channel=self.channel_name,
            thread_ts=self.game["_id"],
            text=":heavy_check_mark: The game has been funded. You can play now!"
        )

    def display_word(self):
        """Display the word so far in the thread"""
        text = f"You've guessed {self.game['template']} so far."

        self.slack_client.chat_postMessage(
            channel=self.channel_name,
            thread_ts=self.game["_id"],
            text=text
        )

    def guess(self, letter, user):

        if not self.game['gp_funded']:  # Game not paid for yet!
            self.slack_client.chat_postMessage(
                channel=self.channel_name,
                thread_ts=self.game["_id"],
                text="Regrettably, this game is not funded yet.",
                as_user=True
            )
            return

        # Lower guess if not case sensitive game
        if not self.game['case_sensitive']:
            letter = letter.lower()

        # Check if letter is a guess for the entire word.
        if letter == self.game['word']:
            self._initiate_win(user)
            return

        # If not, make sure guess is one letter
        if len(letter) != 1:
            return

        # Add user to players if the user isn't the game creator but make sure the user isn't already in this list.
        if self.game['user'].lower() != user.lower() and (user not in self.game['players']):
            self.game['players'].append(user)

        # Make sure the letter isn't repeating.

        if letter in self.game['guesses']:
            # Alter the user and end the function
            self.slack_client.chat_postMessage(
                channel=self.channel_name,
                thread_ts=self.game["_id"],
                text="Regrettably, you've already guessed that letter. Try again!"
            )
            return

        # Add letter to list of guesses
        self.game['guesses'].append(letter)

        # Retain old template for comparison purposes
        old_template = self.game['template']

        # Rebuild the template. We use range so it's easier to replace stuff in the template (word and template are the same length.
        for i in range(len(self.game['word'])):
            # If letter is the current character, replace that in the template
            if self.game['word'][i] == letter:
                self.game['template'] = self.game['template'][:i] + \
                    letter + self.game['template'][(i+1):]

        # Save game
        self.game.save()

        # Check if the template and the word are the same. This means the user won.
        if self.game['template'] == self.game['word']:
            # The user won. Initiate a winning sequence and give it the winning user.
            self._initiate_win(user)
            return

        # The template changed, meaning the guess was correct. Alert the user.
        if old_template != self.game['template']:
            template = self.game['template']
            self.slack_client.chat_postMessage(
                channel=self.channel_name,
                thread_ts=self.game['_id'],
                text=f"The guess was correct!\nThe current word is\n\"{template}\""
            )
        else:
            # The guess was incorrect
            # Decrease attempts for getting it wrong
            self.game['attempts'] -= 1
            self.game.save()  # Save the game again

            # Here the number of attempts might be zero.

            if self.game['attempts'] == 0:
                # User lost
                self._initiate_lose()
                return

            self.slack_client.chat_postMessage(
                channel=self.channel_name,
                thread_ts=self.game['_id'],
                text=f"Regrettably, that guess was wrong.\nYou have {self.game['attempts']} guesses left."
            )

    def _initiate_lose(self):
        """Destroy game"""
        # Get word
        word = self.game['word']

        # Alert user
        self.slack_client.chat_postMessage(
            channel=self.channel_name,
            thread_ts=self.game['_id'],
            text=f'Regrettably, you ran out of attempts.\nThe word was `{word}`.\nBetter luck next time!',
            as_user=True
        )

        # Give out gp
        self._give_gp(None)  # None -> no winner

        # Delete game
        self.game.delete()

    def _initiate_win(self, winner):
        """Initiate winning sequence"""

        # Get word
        word = self.game['word']

        # Alert user
        self.slack_client.chat_postMessage(
            channel=self.channel_name,
            thread_ts=self.game['_id'],
            text=f'Congrats to <@{winner}>!\nThey won the game!\nThe word was `{word}`.',
            as_user=True
        )

        # Give out gp.

        self._give_gp(winner)

        # Delete game

        self.game.delete()

    def _give_gp(self, winner):
        gp = self.game['gp']
        for player in self.game['players']:
            if player != winner:
                self.requests.post(f'{self.banker_api}/give',
                                   json={
                                       "token": self.banker_api_key,
                                       "send_id": player,
                                       "bot_id": self.bot_id,
                                       "gp": 1,
                                       "reason": "participating in a hangman game"
                                   })

        if winner and (winner != self.game['user']):
            self.requests.post(f'{self.banker_api}/give',
                               json={
                                   "token": self.banker_api_key,
                                   "send_id": winner,
                                   "bot_id": self.bot_id,
                                   "gp": gp,
                                   "reason": "winning in a hangman game"
                               })
            self.slack_client.chat_postMessage(
                channel=self.channel_name,
                text=f"Congrats to <@{winner}> for winning in a hangman game! They have just recieved {gp} gp.",
                thread_ts=self.game['_id'],
                as_user=True
            )
        self.slack_client.chat_postMessage(
            channel=self.channel_name,
            text=f"Participants in the game, you each get 1 gp. Thanks for playing hangman!",
            thread_ts=self.game['_id'],
            as_user=True
        )

    def _build_template(self, word):
        """Build template for hangman games"""

        template = ''
        exempted = [' ', ':', '<', '>', '&']
        for c in word:
            # If it's an exempt char, show in the template
            if c in exempted:
                template += c
            # If not an exempt char, add an underscore.
            else:
                template += "‗"

        return template
