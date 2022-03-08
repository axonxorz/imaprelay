import re

from io import StringIO


FOLDER_LINE_RE = re.compile(r'\((?P<flags>.*?)\) "(?P<delimiter>.*)" (?P<name>.*)')


def parse_folder_line(line):
    line = line.decode()
    flags, delimiter, mailbox_name = FOLDER_LINE_RE.match(line).groups()
    mailbox_name = mailbox_name.strip('"')
    return flags, delimiter, mailbox_name


def asbool(value):
    if value is None:
        return False
    value = value.lower()
    return value.startswith('1') or value.startswith('y') or value.startswith('t')
