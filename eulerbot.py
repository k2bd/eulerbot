#!/usr/bin/env python3

import os
import time
import json
from slackclient import SlackClient

solved_problems = {}

# My ID
BOT_ID = os.environ.get("BOT_ID")

# Constants
AT_BOT = "<@" + BOT_ID + ">"
#commands = {"solve","unsolve","leaderboard"}

# Intantiate slack & twilo client
slack_client = SlackClient(os.environ.get('SLACK_BOT_TOKEN'))

def respond(text):
    slack_client.api_call("chat.postMessage",
                          channel=channel,
                          text=text,
                          as_user=True)
    return

def backup(leaderboard):
    outfile = open('bot_backup.txt','w')
    json.dump(leaderboard,outfile)
    outfile.close()

def handle_command(user,command,channel):
    '''
     Recieves a command and parses it.
     Known commands:
      - Solve
        Register a problem as solved by the user
      - Unsolve
        Problem is not actually solved by the user
      - leaderboard
        Print the leaderboard
    '''
    if user == BOT_ID:
        return

    # TODO fix next line with an OOP solution
    id_to_name = getUsers()
    if user not in id_to_name.keys():
        id_to_name = getUsers()

    cmd = command.split()
    if cmd[0] == 'solve':
        # Mark the problem provided as solved
        try:
            prob = int(cmd[1])
        except ValueError:
            respose = "Usage: @eulerbot solve n"
            respond(response)
            return
        if user not in solved_problems:
            solved_problems[user] = []
        if prob not in solved_problems[user]:
            solved_problems[user].append(prob)
            response = "Marked problem "+str(prob)+" as solved by "+id_to_name[user]+"."
            respond(response)
        # Now backup what we've got
        backup(solved_problems)
        return

    elif cmd[0] == 'unsolve':
        # Unsolve a problem that was marked as solved
        try:
            prob = int(cmd[1])
        except ValueError:
            response = "Usage: @eulerbot unsolve n"
            respond(response)
            return
        if user in solved_problems:
            if prob in solved_problems[user]:
                solved_problems[user].remove(prob)
                response = "Marked problem "+str(prob)+" as not solved by "+id_to_name[user]+"."
                respond(response)
        # Now backup what we've got
        backup(solved_problems)
        return
    
    elif cmd[0] == 'leaderboard':
        if len(cmd) > 1:
            try:
                places = int(cmd[1])
            except ValueError:
                pass
        else:
            places = 10

        leaderboard = {} # Reversed dictionary {problem: solver}
        for user in solved_problems:
            for problem in solved_problems[user]:
                unique = True
                for other_user in solved_problems:
                    if user is not other_user:
                        if problem in solved_problems[other_user]:
                            unique = False
                            break
                if unique:
                    leaderboard[problem] = user

        i = 1
        response = '```\n'
        for problem in sorted(leaderboard,reverse=True):
            if i > places:
                break

            response += (str(i)+": "+str(problem)+" "+id_to_name[leaderboard[problem]]+"\n")

            i += 1

        response += '```'
        respond(response)
        return

    elif cmd[0] == 'commands':
        response = "@eulerbot commands:\n"+\
                   "solve n         - marks a problem as solved by you\n"+\
                   "unsolve n       - marks a problem as not solved by you\n"+\
                   "leaderboard [n] - prints the current leaderboard, optionally to n places"
        respond(response)
        return

    response = "Sorry, I didn't understand that."
    respond(response)

def getUsers():
    id_to_name = {}
    userlist = slack_client.api_call("users.list")
    if userlist.get('ok'):
        users = userlist.get('members')
        for user in users:
            id_to_name[user.get('id')] = user['name']
    else:
        print("FAILED - could not get users")
    return id_to_name

def parse_slack_output(slack_rtm_output):
    '''
     The Slack Real Time Messaging API is an events firehose.
     This parsing function returns None unless a message is directed at the Bot, based on its ID
    '''
    output_list = slack_rtm_output
    if output_list and len(output_list) > 0:
        for output in output_list:
            if output and 'text' in output and AT_BOT in output['text']:
                # Return the text after the @ mention of our bot, whitespace removed
                return output['user'],output['text'].split(AT_BOT)[1].strip().lower(),output['channel']
    return None, None, None



if __name__ == '__main__':
    try:
        infile = open("bot_backup.txt",'r')
        solved_problems = json.load(infile)
        infile.close()
    except FileNotFoundError:
        # No backups made yet
        pass

    id_to_name = getUsers()

    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from the firehose
    if slack_client.rtm_connect():
        print("Eulerbot ready.")
        while True:
            user, command, channel = parse_slack_output(slack_client.rtm_read())
            if command and channel:
                handle_command(user, command, channel)
            time.sleep(READ_WEBSOCKET_DELAY)
    else:
        print("Connection failed. Invalid Slack token or bot ID?")
