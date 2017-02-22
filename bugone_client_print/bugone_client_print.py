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
import bugonehelper
import zmq

if __name__ == "__main__":
    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    subscriber.connect("tcp://192.168.42.252:40666")
    subscriber.setsockopt(zmq.SUBSCRIBE,b"")

    while True:
        message = subscriber.recv()
        timestamp = int.from_bytes(message[0:8], byteorder = "big")
        msgtype = message[8]
        nodeid = message[9]
        if msgtype < 2:
            devid = message[10]
            print("%s - (%s,%s) -> %s" % (time.asctime(time.localtime(timestamp)), nodeid, devid, int.from_bytes(message[11:13], byteorder = "big")))



