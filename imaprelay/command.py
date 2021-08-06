import configparser
import logging
import os
import stat
import sys
try:
    from StringIO import StringIO
except:
    from io import StringIO
from . import connection
from . import relay

log = logging.getLogger('imaprelay')

DEFAULT_CONFIG = """\
[relay]
inbox=INBOX
archive=Archive
interval=30
autorespond=False
autorespond_text=""
"""

def main():
    if '-v' in sys.argv:
        log.setLevel(logging.DEBUG)
    if '-c' in sys.argv:
        configfile = sys.argv[sys.argv.index("-c")+1]
    else:
        configfile = os.path.expanduser('~/.secret/imaprelay.cfg')
    log.info("Config loaded from {}".format(configfile))

    st = os.stat(configfile)
    if bool(st.st_mode & (stat.S_IRGRP | stat.S_IROTH)):
        raise Exception("Config file (%s) appears to be group- or "
                        "world-readable. Please `chmod 400` or similar."
                        % configfile)

    config = configparser.ConfigParser()
    config.readfp(StringIO(DEFAULT_CONFIG))
    config.read([configfile])

    connection.configure(config)

    rly = relay.Relay(config.get('relay', 'to'),
                      config.get('relay', 'inbox'),
                      config.get('relay', 'archive'),
                      config.getboolean('relay', 'autorespond'),
                      config.get('relay', 'autorespond_text'),
                      config.get('smtp', 'address'),
                      config.getboolean('relay', 'rate_limit_active'),
                      config.get('relay', 'rate_limit'))
    
    rly.loop(int(config.get('relay', 'interval')))