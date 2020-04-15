#!/usr/bin/python3
import paho.mqtt.client as mqtt
from time import sleep
import argparse
import buttshock.et312
from signal import signal, SIGINT
import sys
import atexit
import fcntl
import configparser

config = configparser.ConfigParser()
config.read('config.ini')
sys.path.append("../buttshock-py/")

modes = {0x76:"Waves", 0x77:"Stroke", 0x78:"Climb", 0x79:"Combo", 0x7a:"Intense", 0x7b:"Rhythm",
         0x7c:"Audio1",0x7d:"Audio2", 0x7e:"Audio3", 0x80:"Random1", 0x81:"Random2", 0x82:"Toggle",
         0x83:"Orgasm",0x84:"Torment",0x85:"Phase1",0x86:"Phase2",0x87:"Phase3",
         0x88:"User1",0x89:"User2",0x8a:"User3",0x8b:"User4",0x8c:"User5",0:"None", 0x7f:"Split"}

powerlevels = {1:"Low (1)",2:"Normal (2)",3:"High (3)"}

# Make sure we exit cleanly and leave the ET312 ready to re-connect
def handler(signal_received, frame):
    print('SIGINT or CTRL-C detected. Exiting gracefully')
    if (et312):
        et312.reset_key()  # reset cipher key so easy resync next time
        et312.close()
    client.loop_stop()
    sys.exit(0)

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    client.subscribe(config['MQTT']['broker_topic'])

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    # TODO: automadom/et312/status  { mode: "Waves", channel_a: 0, channel_b: 10, ma: 50 }
    # TODO: automadom/et312/ramp { channel_a_level: 50, channel_a_ramptime: 4, channel_b_level: 50, channel_b_ramptime: 4 }
    # TODO: automadom/et312/set { channel_a: 50, channel_b: 60 }
    command = msg.topic.split('/')
    if ( command[2] == 'channel_a' ):
        base = 0x4000
        level = int(msg.payload.decode("utf-8"))
        print("Set channel_a to "+str(level))
        et312.write(base+0xac, [0]) # no select
        et312.write(base+0xa8, [0, 0])   # rate, direction
        et312.write(base+0xa5, [level])
        
    if ( command[2] == 'channel_b' ):
        base = 0x4100
        level = int(msg.payload.decode("utf-8"))
        print("Set channel_b to "+str(level))
        et312.write(base+0xac, [0]) # no select
        et312.write(base+0xa8, [0, 0])   # rate, direction
        et312.write(base+0xa5, [level])

    if ( command[2] == 'status' ):
        print("ADC4 (Level A knob)        : {0:#x}".format(et312.read(0x4064)))
        print("ADC5 (Level B knob)        : {0:#x}".format(et312.read(0x4065)))
        print("ADC3 (Battery voltage)        : {0:#x}".format(et312.read(0x4063)))
        print("ADC1 (MA knob)            : {0:#x}".format(et312.read(0x4061)))
        print("    MA scaled value        : %d (mode range %d-%d)" %(et312.read(0x420d),et312.read(0x4086),et312.read(0x4087)))

def on_log(client, userdata, level, buf):
    print("log: ",buf)

def main():
    global et312
    signal(SIGINT, handler)

    # Lock the serial port while we use it, wait a few seconds
    connected = False
    for _ in range(10):
        try:
            et312 = buttshock.et312.ET312SerialSync(config['ET312']['serial_port'])
            if et312.port.isOpen():
                fcntl.flock(et312.port.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                connected = True
            break
        except Exception as e:
            print(e)
            sleep(.2)

    if (not connected):
        print ("Failed to connect to ET312")
        return

    try:
        et312.perform_handshake()

        # this location gets written a 0 when any mode starts, but otherwise unused
        arewerunning = et312.read(0x4093)
        
        if (arewerunning != 42):
            # so let's get it into a blank empty mode. easiest way is calltable 18
            et312.write(0x4078, [0x90]) # mode 90 doesn't exist
            et312.write(0x4070, [18]) # execute mode 90
            while (et312.read(0x4070) != 0xff):
                pass            

            # Overwrite name of current mode with spaces, then display "MQTT"
            et312.write(0x4180, [0x64])
            et312.write(0x4070, [0x15])
            while (et312.read(0x4070) != 0xff):
                pass
            for pos, char in enumerate('MQTT'):
                et312.write(0x4180, [ord(char),pos+9])
                et312.write(0x4070, [0x13])
                while (et312.read(0x4070) != 0xff):
                    pass

            for base in [0x4000,0x4100]:
                et312.write(base+0xa8, [0,0]) # don't increment channel A intensity
                et312.write(base+0xa5, [128]) # A intensity mod value = min
                et312.write(base+0xac, [0]) # no select
                et312.write(base+0xb1, [0]) # rate        
                et312.write(base+0xae, [0x64]) # freq mod
                et312.write(base+0xb5, [4]) # select normal parms
                et312.write(base+0xb7, [0xc8]) # width mod value
                et312.write(base+0xba, [0]) # width mod value        
                et312.write(base+0xbe, [4]) # select normal parms
                et312.write(base+0x9c, [255]) # ramp off
                #et312.write(0x4098,[5,5,1]) # gate it!
            et312.write(0x4093,[42]) # we're provisioned     
                    
    except Exception as e:
        print(e)

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.on_log=on_log
    client.connect(config['MQTT']['broker_ip'], int(config['MQTT']['broker_port']), 60)
    client.loop_forever()

if __name__ == "__main__":
    main()