#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RFD900 Setup Tool."""


import serial, sys, optparse, time
from pexpect import fdpexpect
from yaml import load, dump
from datetime import datetime

parser = optparse.OptionParser("set_speed")
parser.add_option("--baudrate", type="int", default=57600, help="baud rate")
parser.add_option(
    "--config",
    type="string",
    default="config.yaml",
    help="Configuration file for the radio network",
)
parser.add_option("--rtscts", action="store_true", default=False, help="enable rtscts")
parser.add_option("--dsrdtr", action="store_true", default=False, help="enable dsrdtr")
parser.add_option(
    "--xonxoff", action="store_true", default=False, help="enable xonxoff"
)

opts, args = parser.parse_args()

# TODO: add validation
# Multi-POINT COMMANDS
MP_COMMANDS = {
    "air_speed": {"cmd": "ATS2={}", "validator": None},
    "netid": {"cmd": "ATS3={}", "validator": None},
    "txpower": {"cmd": "ATS4={}", "validator": None},
    "ecc": {"cmd": "ATS5={}", "validator": None},
    "rxframe": {"cmd": "ATS6={}", "validator": None},
    "min_freq": {"cmd": "ATS8={}", "validator": None},  # min frequency in kHz
    "max_freq": {"cmd": "ATS9={}", "validator": None},  # max frequency in kHz
    "num_channels": {"cmd": "ATS10={}", "validator": None},  # number of frequency hopping channels.
    "rtscts": {"cmd": "ATS13={}", "validator": None},  # Ready to send and clear to send
    "max_window": {"cmd": "ATS14={}", "validator": None},  # max transmit window size used to limit latency
    "encryption_level": {"cmd": "ATS15={}", "validator": None},  # enable encryption
    "encryption_key": {"cmd": "AT&E={}", "validator": None},  # set key only on 900x
    "target_rssi": {"cmd": "ATR0={}", "validator": None},
    "hysteresis_rssi": {"cmd": "ATR1={}", "validator": None},
    "nodeid": {"cmd": "ATS18={}", "validator": None},
    "nodedestination": {"cmd": "ATS19={}", "validator": None},
    "netcount": {"cmd": "ATS20={}", "validator": None}, # number of networks on the master node
    "masterbackup": {"cmd": "ATS22={}", "validator": None}, # ???? 
    "nodecount0": {"cmd": "AT&M0=0,{}", "validator": None}, # max number of nodes in network 0
    "nodecount7": {"cmd": "AT&M1=7,{}", "validator": None}, # max number of nodes in network 7
    "nodecount13": {"cmd": "AT&M2=13,{}", "validator": None}, # max number of nodes in network 13
}

ASYNC_COMMANDS = {
    "air_speed": {"cmd": "ATS2={}", "validator": None},
    "max_data": {"cmd": "ATS3={}", "validator": None}, # max size of packet data section
    "max_retries": {"cmd": "ATS4={}", "validator": None}, # max number of retries
    "global_retries": {"cmd": "ATS5={}", "validator": None}, # number of retries for broadcast messages
    "txencap": {"cmd": "ATS7={}", "validator": None},
    "rxencap": {"cmd": "ATS8={}", "validator": None},
    "netid": {"cmd": "ATS9={}", "validator": None},
    "nodeid": {"cmd": "ATS10={}", "validator": None},
    "destid": {"cmd": "ATS11={}", "validator": None},
    "txpower": {"cmd": "ATS12={}", "validator": None},
    "mavlink": {"cmd": "ATS13={}", "validator": None},
    "min_freq": {"cmd": "ATS14={}", "validator": None},  # min frequency in kHz
    "max_freq": {"cmd": "ATS15={}", "validator": None},  # max frequency in kHz
    "num_channels": {"cmd": "ATS16={}", "validator": None},  # number of frequency hopping channels.
    "rtscts": {"cmd": "ATS18={}", "validator": None},  # Ready to send and clear to send
    "encryption_level": {"cmd": "ATS19={}", "validator": None},  # enable encryption
    "encryption_key": {"cmd": "AT&E={}", "validator": None},  # set key only on 900x
}

def command(radio_type, key):
    if radio_type == 'MP':
        return MP_COMMANDS[key]["cmd"]
    if radio_type == 'ASYNC':
        return ASYNC_COMMANDS[key]["cmd"]

if len(args) == 0:
    print("usage: rfd900.py <DEVICE...>")
    sys.exit(1)


def parse_firmware(value):
    # RFD ASYNC 2.47 on RFD900xR1.1
    # [2] RFD SiK 2.75MP on RFD900xR1.1
    # RFD SiK 1.9 on RFD900P
    #[1] MP SiK 2.6 on RFD900P
    v = value.decode("utf-8")
    if "ASYNC" in v:
        return "ASYNC"
    if "MP" in v:
        return "MP"

    print("Unknown Firmware version: ", value)
    return None


def load_config():
    """ Load the configuration """
    stream = open(
        opts.config, "r"
    )
    config = load(stream)
    stream.close()
    return config

def enter_command_mode(serial, reset=True):

    try:
        serial.send("+++")
        time.sleep(1)
        serial.expect("OK", timeout=1)
        return True
    except Exception as e:
        print(e)

    if reset: # maybe already in command mode?
        serial.sendline("ATZ")
        time.sleep(3)
        return enter_command_mode(serial, reset=False)

    return None


def configure_radio(device, config):
    """Configure the radio"""
    print(opts.baudrate)
    port = serial.Serial(
        device,
        opts.baudrate,
        timeout=0,
        dsrdtr=opts.dsrdtr,
        rtscts=opts.rtscts,
        xonxoff=opts.xonxoff,
    )

    fout = open("rfd900.log", "ab")
    fout.write(
        "========== {} {} ============ \r\n".format(datetime.now(), device).encode(
            "ascii"
        )
    )
    ser = fdpexpect.fdspawn(port.fileno(), logfile=fout)
    ser.linesep = b"\r\n"
    if not enter_command_mode(ser):
        print("unable to enter command mode. Exiting...")
        exit()

    ser.send("ATI\r\n")

    # print("sent ATI:" , ser.before)
    try:
        #RFD ASYNC 2.47 on RFD900xR1.1
        # [2] RFD SiK 2.75MP on RFD900xR1.1
        ser.expect("RFD900", timeout=2)
        radio_type = parse_firmware(ser.before)
    except fdpexpect.TIMEOUT:
        print("timeout")
        return

    ser.send("ATI8\r\n")
    ser.expect(r"0x([0-9a-fA-F]{16})")
    print("Radio ID is: {}".format(ser.after))
    device_id = ser.after

    to_radio = {**config["common"], **config[device_id.decode("utf-8")]}
    for key, value in to_radio.items():
        print("Setting {} to {}".format(key, value))
        cmd = command(radio_type, key)
        ser.sendline(cmd.format(value).encode("ascii"))
        ser.expect("OK")

    ser.sendline("AT&T") # Disable debug messages
    time.sleep(0.2)
    #ser.expect("OK")

    ser.sendline("AT&W")
    ser.expect("OK")

    ser.sendline("ATI5")
    time.sleep(0.2)
    for _ in range(25):
        ser.readline()

    ser.send("ATZ\r\n")
    time.sleep(1)
    port.close()
    fout.close()

cfg = load_config()
for d in args:
    print("Configuring %s on %s" % (d, opts.config))
    configure_radio(d, cfg)
