"""
Read and parse crontab files.
"""


def parsef(f):
    """ Parse a file object into a generator of (spec, command) tuples. """
    for x in f:
        parsed = parseline(x.rstrip('\n'))
        if parsed is not None:
            yield parsed


def parses(s):
    """ Parse a multiline string object into a generator of (spec, command)
    tuples. """
    for x in s.splitlines():
        parsed = parseline(x)
        if parsed is not None:
            yield parsed


def parseline(line):
    """ Extract the spec and command from a line.  If the line is any kind
    of no-op we return None. """
    if not line:
        return
    # return None if line is commented
    if line[0] == '#':
        return
    if line[0] == '@':
        return tuple(line.split(' ', 1))
    else:
        parts = line.split(' ', 5)
        return ' '.join(parts[:5]), parts[-1]
