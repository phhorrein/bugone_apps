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
import zmq
import bugonehelper
import pickle
import struct
import voluptuous
import yaml
import socket

def format_float_value(v):
    return float(v)/10

def format_mil_value(v):
    return float(v)/1000

def format_bool_value(v):
    return False if v == 0 else True

datatype = {
        "temperature": format_float_value,
        "humidity": format_float_value,
        "voltage": format_mil_value,
        "switch": format_bool_value
        }

device = {
        voluptuous.Optional("display"): str,
        voluptuous.Required("type"): str,
        voluptuous.Required("nodeid"): int,
        voluptuous.Required("devid"): int,
        voluptuous.Optional("format"): int
}
node = {
        voluptuous.Required("location"): str,
        voluptuous.Optional("display"): str,
        voluptuous.Required("nodeid"): int,
        voluptuous.Required("address"): str
}



def validate_db(db):
    schema = voluptuous.Schema({
        voluptuous.Optional("name"): str,
        voluptuous.Required("nodes"): [node],
        voluptuous.Required("devices"): [device]
    })
    try: 
        schema(db)
    except voluptuous.MultipleInvalid as e:
        print(e)


def extract_db(yaml_path):
        if not os.access(os.path.expanduser(yaml_path),os.R_OK):
            print("Error: config file not readable (%s)" % yaml_path)
            sys.exit(1)
        try:
            yaml_file = open(os.path.expanduser(yaml_path),'r')
        except:
            print("Error while opening configuration file")
            sys.exit(1)
        db = yaml.load(yaml_file)
        validate_db(db) 
        return db

if __name__ == "__main__":
    # First, let's parse arguments
    parser = argparse.ArgumentParser(description="BugOne zMQ client to carbon database")
    parser.add_argument("-v","--verbose",action="store_true",help="Verbose output")
    parser.add_argument("-c","--config")

    args = parser.parse_args()
    verbose = args.verbose

    #Default values for parameters (overriden if config file is present)
    log_file = "/tmp/bugone_carbon.log"
    pub_address = "127.0.0.1"
    pub_port = "40666"
    bugone_network_db = "/etc/bugone_client/bugone_network_db.yaml"


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
            pub_address = confparser.get('Server','address')
            pub_port = confparser.get('Server','port')
            bugone_network_db = confparser.get('BugOne','bugone_network_db')
        except configparser.NoSectionError:
            print("Unrecognized config file format")
            sys.exit(1)
    else:
        print("Using default arguments")


    print("DB file: ", bugone_network_db)
    bugone_desc = extract_db(bugone_network_db)



    context = zmq.Context()
    subscriber = context.socket(zmq.SUB)
    url = "tcp://"+pubaddress+":"+pub_port
    subscriber.connect(url)
    subscriber.setsockopt(zmq.SUBSCRIBE,b"")

    while True:
        message = subscriber.recv()
        timestamp = int.from_bytes(message[0:8], byteorder = "big")
        msgtype = message[8]
        nodeid = message[9]
        if msgtype < 2:
            devid = message[10]
            display_name = "Device " + str(nodeid) + "," + str(devid)
            address = "node" + str(nodeid)
            devicename = "dev" + str(devid)
            value = int.from_bytes(message[11:], byteorder="big")
            for node in bugone_desc["nodes"]:
                if node["nodeid"] == nodeid:
                    address = node["address"]
                    break
            for device in bugone_desc["devices"]:
                if device["nodeid"] == nodeid and device["devid"] == devid:
                    display_name = device["display"]
                    devicename = device["type"]
                    value = datatype[device["type"] ](value)
                    print("Converted value: %s" % str(value))
                    break
            path = "bugone." + address + "." + devicename
            payload = pickle.dumps([(path,(timestamp,value))], protocol=2)
            header = struct.pack("!L", len(payload))
            final_msg = header + payload
            print(display_name + ": " + str(final_msg))
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect( ("localhost",2004) )
            s.send(final_msg)
            s.close()
