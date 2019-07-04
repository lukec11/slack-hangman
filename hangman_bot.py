import os
import time
import re
import slack
import copy
import json

BOT_ID = ""
games = {}
channel = "#hangman" # Put your channel here

@slack.RTMClient.run_on(event="message")
def message_on(**payload):
        global BOT_ID
        global channel

        mention = f"<@{BOT_ID}>"
        data = payload["data"]
        web_client = payload['web_client']
        rtm_client = payload['rtm_client']

        if data.get('user'):
                print(BOT_ID == data.get('user'))

        print(f"Test is {data.get('text')}")

#        print("Data is " + str(data))

        if data.get('text') and data.get('user'):

                if data.get('channel')[0] == "D" :
                        try:
                                word, attempts = data.get('text').split(" ")

                                word = word.lower()

                                data = {'user': data.get('user'), 'attempts': int(attempts), 'word': word}
                                data['template'] = ['_' for i in range(len(word))]
                                data['guesses'] = [] # For storing the list of guessed letters.



                                nd = web_client.chat_postMessage(
                                        channel=channel,
                                        text=f"<@{data['user']}> has created a new game! There are {data['attempts']} attempts to guess the word! Your template is:\n {''.join(data.get('template'))}",
                                )

                                print('nd ts ' + nd['ts'])

                                games[nd['ts']] = data

                                print(games)

                        except ValueError:
                                print("Invalid input.")

                elif games.get(data.get('thread_ts')):

                        if BOT_ID != data.get('user'):
                                game = games.get(data.get('thread_ts'))

                                letter = data.get('text')
                                letter = letter.lower()

                                

                                if len(letter) != 1:
                                        nd = web_client.chat_postMessage(
                                                channel=channel,
                                                text=f"Oh noes, that input is invalid!",
                                                thread_ts = data.get('thread_ts')
                                        )

                                        return

                                if letter in game['guesses']:
                                        # Letter already guessed

                                        nd = web_client.chat_postMessage(
                                                channel=channel,
                                                text=f"You already guessed that letter!",
                                                thread_ts = data.get('thread_ts')
                                        )

                                        return


                                word = game.get('word')
                                game['guesses'].append(letter)



                                old_template = copy.deepcopy(game['template'])
                                print("old template " + str(old_template))


                                for i in range(len(word)):
                                        if word[i] == letter:
                                                game['template'][i] = letter

                                print("template is " + "".join(game['template']))

                                print(data.get('user'))
                                print("Guess is " + letter)

                                template = "".join(game['template'])

                                print(old_template)


                                if "".join(game['template']) == game['word']:
                                        nd = web_client.chat_postMessage(
                                                channel=channel,
                                                text=f"You win! The word is {game['word']}!",
                                                thread_ts = data.get('thread_ts')
                                        )
                                        del games[data.get('thread_ts')]


                                elif game['template'] != old_template:
                                        nd = web_client.chat_postMessage(
                                                channel=channel,
                                                text=f"The word is `{template}`!",
                                                thread_ts = data.get('thread_ts')
                                        )


                                elif game['template'] == old_template:
                                        game['attempts'] -= 1
                                        nd = web_client.chat_postMessage(
                                                channel=channel,
                                                text=f"Oh noes! That was wrong!! {game['attempts']} attempts remaining...",
                                                thread_ts = data.get('thread_ts')
                                        )

                                        if game['attempts'] == 0:
                                                nd = web_client.chat_postMessage(
                                                        channel=channel,
                                                        text=f"Oh noes! You ran out of attempts! The word is `{game['word']}`!",
                                                        thread_ts = data.get('thread_ts')
                                                )
                                                del games[data.get('thread_ts')]





with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")) as cf:
          config = json.load(cf)
          slack_token = config["slack_token"]

rtm_client = slack.RTMClient(token=slack_token)

client = slack.WebClient(token=slack_token)
BOT_ID = client.api_call("auth.test")["user_id"]


rtm_client.start()


