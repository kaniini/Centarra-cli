from utils.config import language
from shlex import split
import json


class HookFlags():
    dct = {}

    def __init__(self, **kwargs):
        for i in kwargs:
            tmp = {}
            t = kwargs[i]
            if type(t) is tuple:
                for j in t:
                    if j is True:
                        tmp['param'] = True
                    elif j is False:
                        tmp['param'] = False
                    else:
                        tmp['long'] = j
            elif type(t) is bool:
                tmp['param'] = t
            else:
                tmp['long'] = t
            tmp = dict({'param': False, 'long': None}.items() + tmp.items())
            self.dct[i] = tmp

    def match(self, flag):
        if not flag.startswith('-'):
            a = []
            for i in list(flag[1:]):
                if i in self.dct:
                    a.append((flag, self.dct[flag]['param']))
                else:
                    a.append((False, i))
            return a
        for i in self.dct:
            if self.dct[i]['long'] == flag[1:]:
                return [(i, self.dct[i]['param'])]
        return [False, flag]


class JsonResponse():

    raw_json = {}
    reply = ""
    format = []

    def __init__(self, raw_json, reply, *args):
        self.raw_json = raw_json
        self.reply = reply
        self.format = args

    def form(self):
        return self.reply % tuple(self.format)

    def js(self):
        return json.dumps(self.raw_json, indent=4, separators=(',', ': '))

class CommandError():
    def form(self):
        pass


class HookManager():
    commands = {
        # command name => {'function': function, 'flags': flags,
        # 'min_args': int, 'return_json': bool, 'doc': documentation}
    }

    def command(self, command, flags=HookFlags(), args_amt=0, return_json=True, doc=(language['no_documentation'])):
        if command in self.commands:
            raise NameError(command)

        def wrapped(func):
            self.commands[command] = {'function': func, 'args_amt': args_amt,
                                      'flags': flags, 'return_json': return_json, 'doc': doc}
        return wrapped

    def dispatch(self, raw_command):
        # this is where we hold all of our checking to make sure this command is safe for our plugin.
        # we also make the arguments into some nice easy-to-use objects.
        # this returns the string we want to print out
        args = split(raw_command)  # shlex keeps quoted stuff in one argument
        if len(args) < 1:
            return ""  # they didn't type a command, let's not yell at them for it
        if args[0] == "help":
            return self.help(args[1:])
        command = ' '.join(args[0:2])  # neat, these don't throw errors if the list is too short.
        args = args[2:]
        if not command in self.commands:
            return language['command_not_found']
        command = self.commands[command]
        # we pass an args list and Flags object to the command. we have HookFlags + json flag.
        flags = {}
        wants_json = False
        hook_flags = command['flags']
        i = 0
        while i < len(args):
            if args[i].startswith("-"):
                if args[i] == '--json':
                    args[i] = None
                    wants_json = True
                    i += 1
                    continue
                match = hook_flags.match(args[i][1:])
                for j in match:  # list of tuple(False, i) or (i, False/True)
                    args[i] = None
                    if j[0] is False:
                        print("Flag %s is unknown to this command." % j[1])
                        continue
                    if j[1] is True:
                        i += 1
                        flags[j[0]] = args[i]  # TODO don't let IndexErrors happen
                        continue
                    flags[j[0]] = True
            i += 1
        args = [x for x in args if x is not None]
        if type(command['args_amt']) is int:
            if command['args_amt'] > len(args):
                return language['not_enough_arguments']  # TODO, skip a step and give them the usage.
            elif command['args_amt'] < len(args):
                return language['too_many_arguments']
        else:  # lambda, function.
            if not command['args_amt'](args):
                return language['incorrect_arguments']

        response = command['function'](args, flags)

        if isinstance(response, JsonResponse):
            if wants_json:
                return response.js()
            else:
                return response.form()
        if isinstance(response, CommandError):
            return response.form()

        return response

    def help(self, command):
        # this returns the string we want to print out as help.
        if not command or command == []:
            rply = ""
            for cmd in sorted(self.commands):
                rply += "`%s': %s\r\n" % (cmd, self.commands[cmd]['doc'][0])
            return rply
        if ' '.join(command) in self.commands:
            return '\r\n'.join(self.commands[' '.join(command)]['doc'])
        return language['help']['command_not_found']