import configparser
import logging
import os
import stat
import sys

from . import connection
from . import relay


log = logging.getLogger('imaprelay')


DEFAULT_RELAY_INTERVAL = 60


def main():
    if '-v' in sys.argv:
        log.setLevel(logging.DEBUG)
    if '-c' in sys.argv:
        configfile = sys.argv[sys.argv.index("-c")+1]
    else:
        configfile = os.path.expanduser('~/.secret/imaprelay.cfg')
    log.info("Config loaded from {}".format(configfile))

    try:
        st = os.stat(configfile)
        if bool(st.st_mode & (stat.S_IRGRP | stat.S_IROTH)):
            log.warning(f'Config file {configfile} is group or world readable, this could leak secrets')
    except FileNotFoundError as exc:
        raise Exception('Could not find a valid configuration file') from exc

    config = configparser.ConfigParser()
    config.read([configfile])

    connection.configure(config)

    rly = relay.Relay(to=config.get('relay', 'to'),
                      inbox=config.get('relay', 'inbox'),
                      archive=config.get('relay', 'archive'),
                      smtp_address=config.get('smtp', 'username'))

    interval = DEFAULT_RELAY_INTERVAL
    try:
        interval = config.get('relay', 'interval')
        interval = int(interval)
    except ValueError:
        log.warning(f'Could not parse relay interval {interval}s, using default of {DEFAULT_RELAY_INTERVAL}s')
        interval = DEFAULT_RELAY_INTERVAL
    except configparser.NoOptionError:
        log.warning(f'Relay interval not provided, using default of {DEFAULT_RELAY_INTERVAL}s')

    rly.loop(interval)


if __name__ == '__main__':
    main()
