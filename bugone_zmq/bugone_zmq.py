# -*- coding: utf-8 -*-

"""
Copyright 2017 Pierre-Henri Horrein <ph.horrein@frekilabs.fr>

This is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see
<http://www.gnu.org/licenses/>.

@author: Pierre-Henri Horrein <ph.horrein@frekilabs.fr>
@license: GPL(v3)
"""

import time
import logging
import logging.handlers
import configparser
import argparse
import os
import sys
import bugone
import zmq


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BugOne network bridge to zMQ")
    parser.add_argument("-v","--verbose",action="store_true",help="Verbose output")
    parser.add_argument("-c","--config")

    args = parser.parse_args()
    verbose = args.verbose

    #Default values for parameters (overriden if config file is present)
    log_file = "/tmp/bugone.log"
    serial_port = "/dev/ttyUSB0"
    serial_baudrate = "38400"
    serial_reconnect = False
    pub_address = "localhost"
    pub_port = "40666"

    if args.config: 
        confpath = args.config
        if not os.access(os.path.expanduser(confpath),os.R_OK):
            print("Error: config file not readable (%s)" % confpath)
            sys.exit(1)
        try:
            conffile = open(os.path.expanduser(confpath),'r')
        except:
            print("Error while opening configuration file")
            sys.exit(1)

        try: 
            confparser = configparser.SafeConfigParser()
            confparser.readfp(conffile)
            log_file = confparser.get('General','log_file')
            serial_port = confparser.get('BugOne','serial_port')
            serial_baudrate = confparser.get('BugOne','baudrate')
            serial_reconnect = confparser.getboolean('BugOne','reconnect')
            pub_address = confparser.get('Server','address')
            pub_port = confparser.get('Server','port')
        except configparser.NoSectionError:
            print("Unrecognized config file format")
            sys.exit(1)
    else:
        print("Using default arguments")


    logger = logging.getLogger("BugOneBridge")
    if verbose:
        logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler(log_file)
    if verbose:
        handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(name)s:%(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)

    context = zmq.Context()
    publisher = context.socket(zmq.PUB)
    pub_url = "tcp://"+pub_address+":"+pub_port
    print("Connecting to address %s..." % pub_url)
    publisher.bind(pub_url)
    print("Done, starting the bridge")

    def publish_values(nodeid,devid,value):
        # Publish the results with the following protocol: 
        # First the timestamp in seconds since Epoch in UTC, on 8 bytes (fit for the next "a lot" of years)
        # Second, the type of data being published (0 = config, 1 = values, 2 = node status) (1 byte)
        # Third one is always nodeid (1 byte)
        # Fourth one is devid if type is config or values (1 byte), it does not exist otherwise (0 byte)
        # Last one is variable length payload
        msg = b""
        msg = msg + int(time.time()).to_bytes(8,byteorder = "big")
        msg = msg + bytes([1])
        msg = msg + bytes([nodeid])
        msg = msg + bytes([devid])
        msg = msg + value
        logger.debug("Publishing: %s" % (msg))
        publisher.send(msg)

    bug = bugone.BugOne(serial_port, serial_reconnect, serial_baudrate, logger, publish_values)

    bug.start()

