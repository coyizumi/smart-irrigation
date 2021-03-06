#!/usr/bin/python

import serial
import time
import datetime
import ConfigParser
import sys
import select
import sqlLib

def get_devices():
    ''' Reads from serial_devices.ini and returns a dictionary of devices to read from.

    Return value:
    A dictionary with devices as keys, and dictionaries containing a list of fields and a table as values.

    '''
    # Config file lists all devices to read from as well as the sensor readings to expect
    config = ConfigParser.RawConfigParser( )
    config.read( 'serial_devices.ini' )
    results = {}

    for device in config.options('devices'):
        # Ultimately, all devices will be serial devices. Stdin is supported for testing reasons
        if config.get ('devices', device).lower() == "serial":
            # Here we assume that 9600 baud will work. It may be a good idea to support manually specifying a baud rate.
            stream = serial.Serial(device, 9600)
        else:
            stream = sys.stdin

        # Result is dictionary
        # Handle supporting readline() as key
        # Value is a dict containing a list of fields and a table name
        results[stream] = {    "fields": [x.strip() for x in config.get('format', device).split(',')],
                               "table" : config.get('table', device) }
    return results

def pushSql (results, table=None, col_format=None):
    ''' Uses sqlLib to push a new database entry to the specified table.

    Arguments:
    results   : A dict with database columns as keys, and values for those columns as values.
    table     : (Optional) specifies the database table to push to. Defaults to sqlLib default.
    col_format: (Optional) A list of database column names. Defaults to sqlLib default.

    '''
    sqlLib.initConfig()
    sqlLib.connectDB()
    sqlLib.pushData(results, table, col_format)
    sqlLib.closeDB()

def parseLine (device, col_format, table):
    ''' Parses a line from the given device and pushes it to the database

    Arguments:
    device    : The device to read from. It must support readline()
    col_format: A list containing the names of the columns in the order they will be read in.
    table     : The table to push the received data to.

    '''
    line = device.readline()
    # In future iterations, this should cause some sort of error message and possibly an attempt to reconnect.
    if not line: 
        return False
    # Devices give a tab separated list of sensor readings not including time
    # So we generate the time
    curr_time = datetime.datetime.today().strftime('"%Y-%m-%d %H:%M:%S"')
    # We pull the sensor readings from the input and throw them in a list with time
    results = [curr_time] + line.strip().split('\t')
    # We get the row names of the sensors and append them to "time" the name of the time row
    fields = ["time"] + col_format
    # Then we put the readings in a dictionary with the row names as keys
    results = dict(zip(fields, results))
    # Push results to DB to the table specified by table
    pushSql (results, table=table, col_format=fields)
    # Returning true tells the calling function that this stream is still open
    return True

def main():
    ''' Gets a dictionary of devices from serial_config.ini, then repeatedly reads from the devices and uploads to MySQL server.

    '''
    # Get dictionary with devices as keys and a dictionary containing field names and a table name as values
    device_dict = get_devices()
    # Get list of devices for select to monitor
    devices = device_dict.keys()

    # While there are still open devices
    while devices:
        # Wait for a device to have data ready
        readable, _, _ = select.select(devices, [], [])
        # Then, parse a line from each ready device. If a device is closed, remove it from list
        # Pass into parseLine the list of fields and the table name found in device_dict
        devices = [x for x in readable if parseLine(x, device_dict[x]["fields"], device_dict[x]["table"])]


if __name__ == '__main__':
    main()
