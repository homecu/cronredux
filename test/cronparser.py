"""
Cron parsing tests
"""

import unittest
from cronredux import cronparser


class ParserTests(unittest.TestCase):

    def test_parse_empty(self):
        cases = [
            (''),
            ('# * * * * * totally not running this\n'),
        ]
        for case in cases:
            with self.subTest(case):
                self.assertFalse(cronparser.parseline(case))

    def test_parse_simple_spec(self):
        valid = [
            ('* * * * *', 'command'),
            ('*/1 * * * *', 'command'),
            ('1,2,3 * * * *', 'command'),
            ('1,2,3 * * * *', ' command'),
            ('1,2,3 2,3 * * *', ' command '),
            ('1,2,3 * * * *', ' command more\n'),
        ]
        for x in valid:
            with self.subTest(x):
                self.assertEqual(cronparser.parseline('%s %s' % x), x)

    def test_parse_alias_spec(self):
        valid = [
            ('@daily', 'command'),
        ]
        for x in valid:
            with self.subTest(x):
                self.assertEqual(cronparser.parseline('%s %s' % x), x)

    def test_parse_string(self):
        s = '\n\n* * * * * command\n\n'
        self.assertEqual(list(cronparser.parses(s)),
                         [('* * * * *', 'command')])
