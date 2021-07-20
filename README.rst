imaprelay
=========

``imaprelay`` is a simple tool designed to scratch a very specific itch.
Presented with an institutional email account that he had an obligation
to check, but lacking desire to use the Outlook Web Access interface, the
author was dismayed to find that he was unable to forward his email.

The solution is ``imaprelay``, a python program that logs into an IMAP
account and relays emails from the Inbox to a specified email address,
via an SMTP server. Once relayed, emails are "archived" -- moved out of
the inbox into a different folder.

Although usable programmatically [#code]_, it is expected that most people
will  want to use the ``imaprelay`` command-line tool that this package
provides.

By default, this program will look for a configuration file in
``~/.secret/imaprelay.cfg`` -- its location should indicate that it needs
to contain plain-text passwords for IMAP and SMTP servers, and thus the
program will exit immediately if the file is group- or world-readable.
Alternatively, a path to the configuration file can be provided with the ``-c``.

The available configuration options are listed below::

    # IMAP server connection details
    [imap]
    hostname=imap.exchange.megacorp.com
    username=j.bloggs
    password=123password
    
    # SMTP server connection details
    [smtp]
    hostname=mail.recipient.com
    username=joe_bloggs
    password=passw0rd
    
    # Relay configuration
    [relay]
    # Who should we relay the emails to?
    to=onward@recipient.com
    # Where should we look for emails to be relayed?
    inbox=INBOX
    # Where should we move the emails once successfully relayed?
    archive=Archive

Once you've written a config file, all you need to do is run::

    imaprelay

For verbose logging, use::

    imaprelay -v

To supply a custom path to the config file, use::
    
    imaprelay -c /path/to/config.cfg

To run as a service with systemd, a simple service will do the trick::

    [Unit]
    Description=Imap email relay
    
    [Service]
    Type=simple
    ExecStart=imaprelay -v -c {{path_to_config}}
    Restart=always
    RestartSec=30
    StandardOutput=file:/var/log/imaprelay.log
    StandardError=file:/var/log/imaprelay.log
    SyslogIdentifier=imaprelay

    [Install]
    WantedBy=multi-user.target

Bug reporting
*************

Please report bugs `on Github <http://github.com/nickstenning/imaprelay/issues>`_.


.. [#code] See the ``imaprelay.Relay`` class.
