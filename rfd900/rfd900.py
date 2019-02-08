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
# TODO: add all the commands
COMMANDS = {
    "air_speed": {"cmd": "ATS2={}", "validator": None},
    "netid": {"cmd": "ATS3={}", "validator": None},
    "txpower": {"cmd": "ATS4={}", "validator": None},
    "rxframe": {"cmd": "ATS6={}", "validator": None},
    "min_freq": {"cmd": "ATS8={}", "validator": None},  # min frequency in kHz
    "max_freq": {"cmd": "ATS9={}", "validator": None},  # max frequency in kHz
    "encryption_level": {"cmd": "ATS15={}", "validator": None},  # enable encryption
    "encryption_key": {"cmd": "AT&E={}", "validator": None},  # set key only on 900x
    "target_rssi": {"cmd": "ATR0={}", "validator": None},
    "hysteresis_rssi": {"cmd": "ATR1={}", "validator": None},
    "nodeid": {"cmd": "ATS18={}", "validator": None},
    "nodedestination": {"cmd": "ATS19={}", "validator": None},
}

if len(args) == 0:
    print("usage: rfd900.py <DEVICE...>")
    sys.exit(1)


def parse_firmware(value):
    print("Firmware is: ", value)

def load_config():
    """ Load the configuration """
    stream = open(
        opts.config, "r"
    )
    config = load(stream)
    stream.close()
    return config


def configure_radio(device, config):
    """Configure the radio"""
    port = serial.Serial(
        device,
        opts.baudrate,
        timeout=0,
        dsrdtr=opts.dsrdtr,
        rtscts=opts.rtscts,
        xonxoff=opts.xonxoff,
    )

    fout = open("rfd900.log", "wb+")
    fout.write(
        "========== {} {} ============ \r\n".format(datetime.now(), device).encode(
            "ascii"
        )
    )
    ser = fdpexpect.fdspawn(port.fileno(), logfile=fout)
    ser.linesep = b"\r\n"
    ser.send("+++")
    time.sleep(1)
    ser.expect("OK")
    ser.send("ATI\r\n")

    # print("sent ATI:" , ser.before)
    try:
        # [2] RFD SiK 2.75MP on RFD900xR1.1
        ser.expect("RFD900", timeout=2)
        parse_firmware(ser.before)
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
        cmd = COMMANDS[key]["cmd"]
        ser.sendline(cmd.format(value).encode("ascii"))
        ser.expect("OK")

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
