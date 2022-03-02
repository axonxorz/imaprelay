import configparser
import logging
import os
import stat
import sys
from io import StringIO

from . import connection
from . import relay


log = logging.getLogger('imaprelay')


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
                      autorespond=config.getboolean('relay', 'autorespond'),
                      autorespond_text=config.get('relay', 'autorespond_text'),
                      smtp_address=config.get('smtp', 'hostname'),
                      rate_limit_active=config.getboolean('relay', 'rate_limit_active'),
                      rate_limit=int(config.get('relay', 'rate_limit')),
                      reply_blacklist=config.get('relay', 'reply_blacklist'))
    
    rly.loop(int(config.get('relay', 'interval')))


if __name__ == '__main__':
    main()
