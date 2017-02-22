# zMQ publisher

This tool provide a simple zMQ publisher to interface with the bugOne network.
The tool is a low level bridge, it does not hold information on the
signification of data. It only unwraps the BugOne protocol and sends the raw
received data for each nodes/devices. 

_Please note that only receiving if values is currently supported_

## Format

bugone\_zmq provides a simple data format : 
* 8 bytes for the timestamp. The timestamp is given in seconds from Epoch in the
  UTC timezone. Please note that this timestamp is computed on the server: if
the server time is not set, timestamp will be garbage
* 1 byte for the message type. Three types are currently defined: `values`,
  `config` and `status`
	* `values` (`0x00`) is the simplest type. It contains a value for a given
	  device on a given node
	* `config` (`0x01`) is used to send the configuration for a given device, as
	  sent by the BugOne node
	* `status` (`0x02`) is a _per node_ information. If the packet is a `status`
	  packet, it will only contains the nodeid (see below) followed by a single
byte: 0x00 if the node is inactive, 0xFF if the node is active
* 1 byte for the nodeid
* _(if type is `values` or `config`)_ 1 byte for device id on this node
* n bytes for value. n is 2 if data is an integer, 1 if data is a boolean (0x00
  for false, 0xFF for true), and variable if value is a string. 

All integer values on more than 1 byte (value or timestamp) or sent in a big
endian format. 

## Configuration

The server can be configured using an INI file. A sample file is provided with
the application. 

The configuration file has 3 sections:
* General section holds  general configuration for the application
	* `log_file` : file where logs should be stored
* BugOne section holds bugone sniffer configuration
	* `serial_port`: serial port which should be used to connect to the sniffer
	* `baudrate`: baudrate for the serial communication
	* `reconnect`: if set to yes, the server will try to reconnect to the serial
	  port when connection fails. If set to no, the server will quit when
connection fails. 
	* `number_can_change`: if set to yes, try to change the number of the serial
	  port until we find "something". This is useful if you are using a
serial-USB adapter: the serial port numbering can vary when you disconnect and
reconnect the cable
* Server section holds zMQ configuration
	* `pub_address`: holds the address where the zMQ publisher will bind. Use
	  "0.0.0.0" if you want to bind to all address
	* `pub_port`: TCP port used for publisher binding. Default is 40666

