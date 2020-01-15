#!/usr/bin/env python
"""
tell.py - Phenny Tell and Ask Module
Copyright 2008, Sean B. Palmer, inamidst.com
Licensed under the Eiffel Forum License 2.

http://inamidst.com/phenny/
"""

import datetime
import random
from collections import Counter
from modules import caseless_list
from tools import GrumbleError, read_db, write_db

maximum = 4

# nick aliases (saved in ~/<User phenny dir>/<nick>-<host>.alias.db)
# format (each row is an alias group, aliases are separated by '\t'): 
#
# spectre\tspectie\tspectei
# nick\talias
nick_aliases = [] #don't change this, use the '.alias add' command on the bot

# pending alias pair requests
# reset each session
nick_pairs = []

def aliasGroupFor(nick1):
    # Returns a list containing all aliases for nick1 (including nick1)
    # If there are no recorded aliases, it returns a list only containing nick1
    for alias_group in nick_aliases:
        if nick1 in alias_group:
            return alias_group
    return [nick1]

def aliasPairMerge(phenny, nick1, nick2):
    #Merges the alias group that nick1 is in with the one nick2 is in
    #The resulting group is stored in nick_aliases
    group1 = aliasGroupFor(nick1)
    if len(group1) > 1: #group is in nick_aliases
        nick_aliases.remove(group1)

    group2 = aliasGroupFor(nick2)
    if len(group2) > 1: #group is in nick_aliases
        nick_aliases.remove(group2)

    group1.extend(group2)

    nick_aliases.append(group1)

    dumpAliases(phenny)

def alias(phenny, raw):
    if raw.group(1) :
        if raw.group(1) == 'add':
            nick1 = raw.nick
            nick2 = raw.group(2)
            if (nick2 == None):
                phenny.reply("Usage: .alias add <nick>")
            elif (nick1 == nick2):
                phenny.reply("I don't think that will be necessary.")
            elif (nick2 in aliasGroupFor(nick1)):  
                phenny.reply("You and " + nick2 + " are already paired.")
            elif ([nick2, nick1] in nick_pairs):
                nick_pairs.remove([nick2, nick1])
                aliasPairMerge(phenny, nick1, nick2)
                phenny.reply("Confirmed alias request with " + nick2 + ". Your current aliases are: " + ', '.join(aliasGroupFor(nick1)) + ".")
            elif ([nick1, nick2] in nick_pairs):
                phenny.reply("Alias request already exists. Switch your nick to " + nick2 + " and call \".alias add " + nick1 + "\" to confirm.")
            else:
                nick_pairs.append([nick1, nick2])
                phenny.reply("Alias request created. Switch your nick to " + nick2 + " and call \".alias add " + nick1 + "\" to confirm.")
        elif raw.group(1) == 'list':
            if raw.group(2):
                nick = raw.group(2)
                phenny.reply("%s's current aliases are: " % nick + ', '.join(aliasGroupFor(nick)) + ".")
            else:
               phenny.reply("Your current aliases are: " + ', '.join(aliasGroupFor(raw.nick)) + ".")
        elif raw.group(1) == 'remove':
            nick = raw.nick
            group = aliasGroupFor(nick)
            if len(group) > 1:
                nick_aliases.remove(group)
                group.remove(nick)
                nick_aliases.append(group)
                dumpAliases(phenny)
            phenny.reply("You have removed %s from its alias group" % nick)
        else:
            phenny.reply("Usage: .alias add <nick>, .alias list <nick>?, .alias remove")
    else:
        phenny.reply("Usage: .alias add <nick>, .alias list <nick>?, .alias remove")

alias.rule = r'\.alias(?:\s(\S+))?(?:\s(\S+))?'

def loadAliases(self):
    try:
        nick_aliases = read_db(self, 'alias')
    except GrumbleError:
        nick_aliases = []

def dumpAliases(self):
    write_db(self, 'alias', nick_aliases)

def loadReminders(self):
    try:
        self.reminders = read_db(self, 'tell')
    except GrumbleError:
        self.reminders = {}

def dumpReminders(self):
    write_db(self, 'tell', self.reminders)

def setup(self):
    loadReminders(self)
    loadAliases(self)

def f_remind(phenny, input, verb):
    teller = input.nick

    # @@ Multiple comma-separated tellees? Cf. Terje, #swhack, 2006-04-15
    tellee, msg = input.groups()

    aliases = aliasGroupFor(teller)

    tellee_original = tellee.rstrip('.,:;')
    tellee = tellee_original.lower()

    if len(tellee) > 20: 
        return phenny.reply('That nickname is too long.')

    timenow = datetime.datetime.utcnow().strftime('%d %b %Y %H:%MZ')

    if tellee in aliases: 
        phenny.say('You can %s yourself that.' % verb)
    elif not tellee in (teller.lower(), phenny.nick.lower(), 'me'): # @@
        # @@ <deltab> and year, if necessary
        warn = False
        if tellee_original not in phenny.reminders: 
            phenny.reminders[tellee_original] = [(teller, verb, timenow, msg)]
        else: 
            # if len(phenny.reminders[tellee]) >= maximum: 
            #     warn = True
            phenny.reminders[tellee_original].append((teller, verb, timenow, msg))
        # @@ Stephanie's augmentation
        response = "I'll pass that on when %s is around." % tellee_original
        # if warn: response += (" I'll have to use a pastebin, though, so " + 
        #                              "your message may get lost.")

        rand = random.random()
        if rand > 0.9999: response = "yeah, yeah"
        elif rand > 0.999: response = "yeah, sure, whatever"

        phenny.reply(response)
    else: phenny.say("Hey, I'm not as stupid as Monty you know!")

    dumpReminders(phenny)

def f_tell(phenny, input):
    f_remind(phenny, input, 'tell')
f_tell.rule = ('$nick', ['tell'], r'(\S+) (.*)')
f_tell.thread = False

def f_ask(phenny, input):
    f_remind(phenny, input, 'ask')
f_ask.rule = ('$nick', ['ask'], r'(\S+) (.*)')
f_ask.thread = False

def formatReminder(r, tellee, recipient=None):
    if not recipient:
        recipient = tellee
    teller, verb, dt, msg = r
    template = "%s: %s <%s> %s %s %s"
    today = datetime.datetime.utcnow().strftime('%d %b')
    year = datetime.datetime.utcnow().strftime('%Y ')
    if dt.startswith(today):
        dt = dt[len(today)+1:]
    if year in dt:
        dt = dt.replace(year, '')
    return template % (recipient, dt, teller, verb, tellee, msg)

def getReminders(phenny, channel, key, recipient):
    lines = []
    for reminder in phenny.reminders[key]:
        lines.append(formatReminder(reminder, key, recipient))

    try: del phenny.reminders[key]
    except KeyError: phenny.msg(channel, 'Er...')
    return lines

def message(phenny, input): 
    if not input.sender.startswith('#'): return

    tellee = input.nick
    aliases = caseless_list(aliasGroupFor(tellee))
    channel = input.sender

    reminders = []
    remkeys = list(reversed(sorted(phenny.reminders.keys())))
    for remkey in remkeys:
        if not remkey.endswith('*') or remkey.endswith(':'): 
            if remkey.casefold() in aliases:
                reminders.extend(getReminders(phenny, channel, remkey, tellee))
        elif tellee.casefold().startswith(remkey.casefold().rstrip('*:')): 
            reminders.extend(getReminders(phenny, channel, remkey, tellee))

    for line in reminders[:maximum]: 
        if "**pm**" in line:
            line = line.replace("**pm**", "")
            phenny.msg(tellee, line)
        else:
            phenny.say(line)

    if reminders[maximum:]: 
        phenny.say('Further messages sent privately')
        for line in reminders[maximum:]: 
            phenny.msg(tellee, line)

    if len(list(phenny.reminders.keys())) != remkeys: 
        dumpReminders(phenny)
message.rule = r'(.*)'
message.priority = 'low'
message.thread = False

def messageAlert(phenny, input):
    aliases = aliasGroupFor(input.nick)
    remkeys = set(map(str.lower, phenny.reminders.keys()))
    if any((alias.lower() in remkeys) for alias in aliases):
        phenny.say(input.nick + ': You have messages. Say something, and I\'ll read them out.')
messageAlert.event = 'JOIN'
messageAlert.rule = r'.*'
messageAlert.priority = 'low'
messageAlert.thread = False

def datesort(tell):
    dt = tell[0][2]
    try:
        return datetime.datetime.strptime(dt, '%d %b %Y %H:%MZ')
    except ValueError:
        # message was created before addition of year, assume 2014
        t = datetime.datetime.strptime(dt, '%d %b %H:%MZ')
        return t + (datetime.datetime(year=2014, month=1, day=1) - datetime.datetime(year=t.year, month=1, day=1))

def tells(phenny, input):
    """
Usage: ".tells" for a summary of queued reminders; ".tells [show ]<nick/num>" for reminders queued to a specific nick; ".tells rm <num>" to delete a reminder
    """
    teller = input.nick
    tells = []
    for tellee in phenny.reminders:
        for msg in phenny.reminders[tellee]:
            if teller == msg[0]:
                tells.append((msg, tellee))
    tells = sorted(tells, key=lambda x: datesort(x)) # consistently sort the list by date

    if tells:
        if input.group(1):
            if input.group(1) in ('rm', 'del'):
                if input.group(2).isdigit() and int(input.group(2)) <= len(tells):
                    msg, tellee = tells[int(input.group(2))-1]
                    phenny.reminders[tellee].remove(msg)
                    if not phenny.reminders[tellee]:
                        del phenny.reminders[tellee]
                    phenny.reply('Removed reminder {} that would have sent to {}. (reminder numbers have changed, use ".tells show" again)'.format(input.group(2), tellee))
                else:
                    phenny.reply("That isn't a valid reminder.")
            else:
                search_term = input.group(2) or input.group(1)
                if search_term.isdigit() and int(search_term) <= len(tells):
                    filtered_tells = [tells[int(search_term)-1]]
                else:
                    filtered_tells = list(filter(lambda x: x[1]==search_term, tells))
                if not filtered_tells:
                    phenny.reply('No tells found.')

                pmflag = False
                send_pms = len(filtered_tells) > 2
                for this_index, (msg, tellee) in enumerate(filtered_tells):
                    reminder = '[{}] - {}'.format(tells.index((msg, tellee))+1, formatReminder(msg, tellee))
                    if '**pm**' in reminder or (send_pms and this_index > 1):
                        pmflag = True
                        phenny.msg(teller, teller + ': ' + reminder)
                    else:
                        phenny.reply(reminder)
                if pmflag:
                    phenny.reply('Additional reminders sent via pm')
        else:
            count = Counter([i for (_, i) in tells])
            phenny.reply('You have the following tells: ' + ', '.join(sorted(['{} ({})'.format(tellee, cnt) for tellee, cnt in count.items()])))
    else:
        phenny.reply("You don't have any tells queued.")
tells.rule = r'\.tells(?:\s(rm|del|show|[\d\w]+)(?:\s([\d\w]+))?)?$'

if __name__ == '__main__': 
    print(__doc__.strip())
