#!/usr/bin/python
#-*- coding: utf-8 -*-
"""
Copyright 2017 MDL 

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

This file is part of the BugOne project 
https://github.com/jkx/DIY-Wireless-Bug
"""

### Packet types ###

PACKET_HELLO  = 0x01
PACKET_PING   = 0x02
PACKET_PONG   = 0x03
PACKET_GET    = 0x04
PACKET_SET    = 0x05
PACKET_VALUES = 0x06
PACKET_SLEEP = 0x07
PACKET_GETCONFIG = 0x08
PACKET_CONFIG = 0x09

APP_TEMPERATURE = 0 
APP_HUMIDITY = 1 
APP_BATTERY = 2 
APP_BANDGAP = 3 
APP_EVENT = 4 
APP_SWITCH = 5 
APP_LUM = 6 
APP_DIMMER = 7 
APP_CONFIG = 8 


### Read packet ###

def getPacketSrc(message):
	return message[0]

def getPacketDest(message):
	return message[1]

def getPacketRouter(message):
	return message[2]

def getPacketType(message):
	return message[3]

def getPacketCounter(message):
	return readInteger(message[4:6])

def getPacketData(message):
	return message[6:]

### Parse data ###

def readValues(data):
	values = []
	while len(data) > 3:
		srcDevice = data[0]
		destDevice = data[1]
		valueType = data[2]
		value = None
		if valueType == ord('I'):
			valueInt = readInteger(data[3:5])
			value = valueInt.to_bytes(2,byteorder="big")
			data = data[5:]
		elif valueType == ord('S'):
			count = data[3]
			valueInt = 0
			value = data[4:4+count]
			data = data[4+count:]
		else:
			break
		values.append((srcDevice, destDevice, value, valueInt))
	return values

def readConfigs(data):
    configs = []
    num = data[0]
    data = data[1:]
    while num > 0:
        srcDevice = data[0]
        srcType = data[1]
        data = data[2:]
        configs.append((srcDevice, srcType))
        num = num - 1
    return configs

def writeValues(values):
	data = ""
	for (srcDeviceId, destDeviceId, value) in values:
		data += chr(srcDeviceId)
		data += chr(destDeviceId)
		if type(value) is int:
			data += 'I' + writeInteger(value)
		elif type(value) is str:
			data += 'S' + chr(len(value)) + value
	return data

def writeDevices(devices):
	data = ""
	for (srcDeviceId, destDeviceId) in devices:
		data += chr(srcDeviceId)
		data += chr(destDeviceId)
	return data

### Send packet ###

def hello(sniffer):
	sniffer.send(buildPacket(0xFF, PACKET_HELLO))

def ping(destNodeId, sniffer):
	sniffer.send(buildPacket(destNodeId, PACKET_PING))

def pong(destNodeId, sniffer):
	sniffer.send(buildPacket(destNodeId, PACKET_PONG))

def setValue(destNodeId, srcDeviceId, destDeviceId, value, sniffer):
	data = writeValues([(srcDeviceId, destDeviceId, value),(0xFF,0xFF,0)])
	sniffer.send(buildPacket(destNodeId, PACKET_SET, data=data))

def getValue(destNodeId, srcDeviceId, destDeviceId, sniffer):
	data = writeDevices([(srcDeviceId, destDeviceId),(0xFF,0xFF)])
	sniffer.send(buildPacket(destNodeId, PACKET_GET, data=data))
	message = sniffer.waitForMessage()
	if message and getPacketType(message) == PACKET_VALUES:
		values = readValues(getPacketData(message))
		return values[0][2]
	return None

### TOOLS ###

# return packet formatted according bugOne protocol (do not send)
# packetType can be: 1 Hello, 2 Ping, 3 Pong, 4 Get, 5 Set, 6 Values
def buildPacket(destNodeId, packetType, srcNodeId = 0, lastCounter = 0, data = None):
	message  = chr(srcNodeId)   # Src
	message += chr(destNodeId)  # Dest
	message += chr(0)           # Router
	message += chr(packetType)  # Type
	message += writeInteger(lastCounter) # Counter
	if data:
		message += data
	return message

def readInteger(bytes, bigEndian = True):
	res = 0
	if bigEndian: bytes = bytes[::-1]
	for b in bytes:
		res = res << 8
		res += b
	return res

def writeInteger(value):
	return chr(value & 0x00FF) + chr((value & 0xFF00) >> 8)

