import email
import imaplib
import smtplib
import socket
import logging
import datetime
import time
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid
from .import util
from .connection import make_imap_connection, make_smtp_connection

log = logging.getLogger(__name__)

BATCH_SIZE = 10


class RelayError(Exception):
    pass


class IMAPError(RelayError):
    pass


class Relay(object):
    def __init__(self,
                 to: str,
                 inbox: str,
                 archive: str,
                 autorespond: bool = False,
                 autorespond_text: str = None,
                 smtp_address: str = None,
                 rate_limit_active: bool = True,
                 rate_limit: int = 5,
                 reply_blacklist: str = "no-reply@*;noreply@*"):
        self.to = to
        self.inbox = inbox
        self.archive = archive
        self.autorespond = autorespond
        self.autorespond_text = autorespond_text
        self.smtp_address = smtp_address
        self.rate_limit_active = rate_limit_active
        self.start_rate_period = datetime.datetime.now()
        self.rate_counter = 0
        self.rate_limit = rate_limit  # Reply mails per minute
        self.reply_blacklist = reply_blacklist

    def relay(self):
        try:
            return self._relay()
        finally:
            self._close_connections()

    def _relay(self):
        if not self._open_connections():
            log.warn("Aborting relay attempt")
            return False

        data = self._chk(self.imap.list())
        folders = [util.parse_folder_line(line)[2] for line in data]

        if self.inbox not in folders:
            raise RelayError('No "{0}" folder found! Where should I relay messages from?'.format(self.inbox))

        if self.archive not in folders:
            raise RelayError('No "{0}" folder found! Where should I archive messages to?'.format(self.archive))

        data = self._chk(self.imap.select(self.inbox))

        log.info('Relaying {num} messages from {inbox}'.format(num=data[0].decode(), inbox=self.inbox))

        # Take BATCH_SIZE messages and relay them
        def get_next_slice():
            data = self._chk(self.imap.search(None, 'ALL'))
            msg_ids = [x for x in data[0].decode().split(' ') if x != '']
            msg_slice, msg_ids = msg_ids[:BATCH_SIZE], msg_ids[BATCH_SIZE:]
            return msg_slice

        msg_slice = get_next_slice()
        while msg_slice:
            if self.autorespond:
                self._autorespond(msg_slice)
            self._relay_messages(msg_slice)
            msg_slice = get_next_slice()

        return True

    def _relay_messages(self, message_ids):
        log.debug("Relaying messages {0}".format(message_ids))

        # Get messages and relay them
        message_ids = ','.join(message_ids)
        msg_data = self._chk(self.imap.fetch(message_ids, '(RFC822)'))

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                eml = email.message_from_bytes(response_part[1])

                res = self.smtp.sendmail(eml['from'], self.to, eml.as_string())

                log.debug("Sent message '{subj}' from {from_} to {to}".format(from_=eml['from'],
                                                                              to=self.to,
                                                                              subj=eml['subject']))

        # Copy messages to archive folder
        # self._chk(self.imap.copy(message_ids, self.archive))

        # Mark messages as deleted on server
        # self._chk(self.imap.store(message_ids, '+FLAGS', r'(\Deleted)'))

        # Expunge
        # self._chk(self.imap.expunge())

    def _check_rate_limit(self):
        interval = datetime.timedelta(minutes=1)
        time_delta = datetime.datetime.now() - self.start_rate_period
        if time_delta < interval:
            if self.rate_counter < self.rate_limit:
                log.debug("No rate limit, only {num} messages sent this period".format(num=self.rate_counter))
                self.rate_counter += 1
                return True
            else:
                log.debug("Reply blocked, rate this period exceeded")
                return False
        else:
            self.start_rate_period = datetime.datetime.now()
            log.debug("No rate limit, only 0  messages sent this period")
            self.rate_counter = 1
            return True

    def _check_blacklist(self, recipient):
        rules = self.reply_blacklist.split(';')
        compiled_rules = map(lambda x: re.compile(x, re.IGNORECASE), rules)
        for s, r in zip(rules, compiled_rules):
            m = r.match(recipient)
            if m:
                log.debug("Reply blocked, recipient {re} matched blacklist rule {ru}".format(re=recipient, ru=s))
                return False
        return True

    def _autorespond(self, message_ids):
        log.debug("Autoresponding messages {0}".format(message_ids))

        # Get messages and relay them
        message_ids = ','.join(message_ids)
        msg_data = self._chk(self.imap.fetch(message_ids, '(RFC822)'))

        for response_part in msg_data:
            if isinstance(response_part, tuple):
                eml = email.message_from_bytes(response_part[1])
                autoreply = MIMEMultipart('alternative')
                autoreply['Message-ID'] = make_msgid()
                autoreply['References'] = eml['Message-ID']
                autoreply['In-Reply-To'] = eml['Message-ID']
                autoreply['Subject'] = f"Re: {eml['Subject']}"
                autoreply['From'] = self.smtp_address
                autoreply['To'] = eml['Reply-To'] or eml['From']
                autoreply.attach(MIMEText(self.autorespond_text.replace("\\n", "\n"), 'plain'))

                # do not send if rate limi exceeded
                if self.rate_limit_active and not self._check_rate_limit():
                    break
                
                # do not send if blacklisted
                if not self._check_blacklist(autoreply['To']):
                    continue
                    
                try:
                    res = self.smtp.sendmail(autoreply['From'], autoreply['To'], autoreply.as_bytes())
                    log.debug("Sent autorespond message '{subj}' from {from_} to {to}".format(
                        from_=autoreply['From'],
                        to=autoreply['To'],
                        subj=autoreply['Subject']))
                except Exception as e:
                    log.error("Failed to autoreply to {to}. Maybe its a noreply address? {e}".format(to=autoreply['To'], e=e))

    def loop(self, interval=30):
        try:
            while 1:
                r = self.relay()
                t = interval if r else interval * 10
                log.info("Sleeping for %d seconds", t)
                time.sleep(t)
        except KeyboardInterrupt:
            log.warn("Caught interrupt, quitting!")

    def _open_connections(self):
        try:
            self.imap = make_imap_connection()
        except (socket.error, imaplib.IMAP4.error):
            log.exception("Got IMAP connection error!")
            return False

        try:
            self.smtp = make_smtp_connection()
        except (socket.error, smtplib.SMTPException):
            log.exception("Got SMTP connection error!")
            return False

        return True

    def _close_connections(self):
        log.info('Closing connections')

        try:
            self.imap.close()
        except (imaplib.IMAP4.error, AttributeError):
            pass

        try:
            self.imap.logout()
        except (imaplib.IMAP4.error, AttributeError):
            pass

        try:
            self.smtp.quit()
        except (smtplib.SMTPServerDisconnected, AttributeError):
            pass

    def _chk(self, res):
        typ, data = res
        if typ != 'OK':
            raise IMAPError("typ '{0}' was not 'OK!".format(typ))
        return data
