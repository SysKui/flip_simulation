import gdb


class BuildCmd(gdb.Command):
    def __init__(self, target):
        self.__doc__ = target.__doc__
        super(BuildCmd, self).__init__(target.__name__, gdb.COMMAND_USER)
        self.target = target

    def complete(self, text, word):
        return gdb.COMPLETE_NONE

    def invoke(self, args, from_tty):
        return self.target(args)
