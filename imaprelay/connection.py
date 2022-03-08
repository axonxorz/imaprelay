import imaplib
import smtplib
import logging

from imaprelay.util import asbool


log = logging.getLogger(__name__)

_config = None


def configure(config):
    global _config
    _config = config


def make_imap_connection():
    # Connect to the server
    hostname = _config.get('imap', 'hostname')
    log.info('Connecting to IMAP server {0}'.format(hostname))
    connection = imaplib.IMAP4_SSL(hostname)

    # Login to our account
    username = _config.get('imap', 'username')
    password = _config.get('imap', 'password')
    log.info('Logging in to IMAP as {0}'.format(username))
    connection.login(username, password)

    return connection


def make_smtp_connection():
    # Connect to the server
    hostname = _config.get('smtp', 'hostname')
    smtp_ssl = asbool(_config.get('smtp', 'ssl'))
    smtp_starttls = asbool(_config.get('smtp', 'starttls'))

    if smtp_ssl and smtp_starttls:
        raise ValueError('Cannot use SSL and STARTTLS')

    log.info('Connecting to SMTP server {0} (ssl={1}, starttls={2})'.format(hostname, smtp_ssl, smtp_starttls))

    if smtp_ssl:
        smtp_cls = smtplib.SMTP_SSL
    else:
        smtp_cls = smtplib.SMTP

    conn_args = [hostname]
    connection = smtp_cls(*conn_args)
    connection.ehlo()

    if smtp_starttls:
        connection.starttls()

    # Login to our account
    username = _config.get('smtp', 'username')
    password = _config.get('smtp', 'password')
    if username and password:
        log.info('Logging in to SMTP as {0}'.format(username))
        connection.login(username, password)

    return connection
