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
import asyncio
import serial.aio
import bugonehelper
import logging
import logging.handlers



class BugOneProtocol(asyncio.Protocol):

    def __init__(self, cb_process,log = None):
        if log :
            self.log = log

        self._process_data = cb_process

        self.waiting = False
        self.length = 0
        self.data = b""
        self.received = 0
        self.errors = 0


    def connection_made(self, transport):
        self.transport = transport
        self.log.debug("Serial port opened")
        transport.serial.rts = False

    def connection_lost(self, exc):
        self.log.debug("Port closed")
        ayncio.get_event_loop().stop() # No reconnect for now

    def data_received(self, data):
        while len(data) > 0:
            # Check if we are already waiting for a packet
            if not self.waiting:
                self.length = data[0]
                data = data[1:]
                # BugOne packets are always 32 bytes long
                if self.length != 32:
                    self.log.error("Received impossible length (%s), we should discard" % str(self.length))
                    self.length = 32
                    self.errors = self.errors + 1
                    # TODO : add timeout to discard
                self.length += 1 # Add checksum
                self.waiting = True
                self.data = b""

            # We still have self.length bytes to read, and we just received len(data)
            to_read = min(len(data), self.length)
            if to_read != 0:
                last_idx = to_read
                self.data = self.data + data[0:last_idx]
                data = data[last_idx:]
                self.length -= to_read

            if self.length == 0: 
                self.received = self.received + 1
                c = 0
                for i in self.data:
                    c ^= i
                if c != 0:
                    self.log.error('Erroneous data...')
                    self.errors = self.errors + 1
                self._process_data(self.data)
                self.log.debug('%s received, %s errors' % (self.received, self.errors))
                self.waiting = False
                self.data = b""
            if (len(data)) != 0:
                self.log.debug("Proceed with next data (length: %s)" % (len(data)))

    def send_data(self,data):
        self.log.debug('Sending data', repr(data))
        transport.write(data)

class BugOne():

    def __init__(self, port, autoreconnect, baudrate, log, cb = None):
        self.port = port
        self.autoreconnect = autoreconnect
        self.baudrate = baudrate
        self.log = log
        self.glob_cb = cb
        self.registered_devices = {}
        self.registered_nodes = {}

    def start(self):
        self.loop = asyncio.get_event_loop()
        coro = serial.aio.create_serial_connection(self.loop, lambda: BugOneProtocol(self.process_data,self.log), self.port, baudrate = self.baudrate)
        self.loop.run_until_complete(coro)
        self.loop.run_forever()
        self.loop.close()

    def register_device(self,nodeid,devid,cb_function):
        # Register to update from (nodeid,devid) device
        # When something happens on this device, call cb_function
        # cb_function taks nodeid, devid and a bytearray or integer (value) as arguments
        self.registered_devices.setdefault( (nodeid,devid) , [])
        self.registered_devices[ (nodeid,devid) ].append(cb_function)

    def register_node(self,nodeid,cb_function_node, cb_function_dev = None):
        # Register to update from nodeid. 
        # By default, only "Node wide" updates trigger the callback (cb_function_node). 
        # This callback takes the nodeid and status (boolean) as argument
        # If cb_function_dev is provided, it will be called for all devices of the node
        self.registered_nodes.setdefault( (nodeid) , [] )
        self.registered_nodes[ (nodeid) ].append( (cb_function_node,cb_function_dev) )

    def process_data(self,data):
        messageType = bugonehelper.getPacketType(data)
        srcNodeId = bugonehelper.getPacketSrc(data)
        destNodeId = bugonehelper.getPacketDest(data)
        counter = bugonehelper.getPacketCounter(data)
        status = True
        self.log.info(u"Message [%s] from %s to %s" % (counter, hex(srcNodeId), hex(destNodeId)))
        if messageType == bugonehelper.PACKET_HELLO:
            self.log.debug("Hello")
        elif messageType == bugonehelper.PACKET_PING:
            self.log.debug("Ping")
        elif messageType == bugonehelper.PACKET_PONG:
            self.log.debug("Pong")
        elif messageType == bugonehelper.PACKET_VALUES:
            values = bugonehelper.readValues(bugonehelper.getPacketData(data))
            for (srcDevice, destDevice, value, valueInt) in values:
                self._run_cb(srcNodeId,srcDevice,value)
                self.log.info("(%s.%s) -> (%s.%s) = %s" % \
                    (srcNodeId, srcDevice, destNodeId, destDevice, valueInt))
        elif messageType == bugonehelper.PACKET_SLEEP:
            status = False
            self.log.debug("Sleep packet")
        elif messageType == bugonehelper.PACKET_CONFIG:
            configs = bugonehelper.readConfigs(bugonehelper.getPacketData(data))
            for (srcDevice, srcType) in configs: 
                self.log.info("Node has device %s with type %s" % (str(srcDevice),str(srcType)))
        else:
            self.log.debug([hex(i) for i in bugonehelper.getPacketData(data)])
        self._report_status(srcNodeId,status)


    def _report_status(self,nodeid,status):
        if nodeid in self.registered_nodes:
            for (cb_node, cb_dev) in self.registered_nodes[ nodeid ]:
                cb_node(nodeid,status)

    def _run_cb(self,nodeid,devid,value):
        if self.glob_cb:
            self.glob_cb(nodeid,devid,value)
        if (nodeid,devid) in self.registered_devices:
            for cb in self.registered_devices[ (nodeid,devid) ]:
                cb(nodeid,devid,value)
        if nodeid in self.registered_nodes:
            for (cb_node, cb_dev) in self.registered_nodes[ nodeid ]:
                if cb_dev: 
                    cb_dev(nodeid,devid,value)

if __name__ == "__main__":
    logger = logging.getLogger("BugOneBridge")
    logger.setLevel(logging.DEBUG)

    handler = logging.handlers.SysLogHandler()
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(name)s:%(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    bugone = BugOne("/dev/ttyUSB0", False, 38400, logger)
    bugone.start()

