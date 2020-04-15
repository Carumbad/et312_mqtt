# et312_mqtt
This is a very basic script which subscribes to an MQTT topic and then controls a USB connected ErosTek ET312 device.

It is 90% a copy of the `shockcade` script provided as part of the buttshock-py package, on which this relies on entirely for it's communication with the ET312.

# How To Use
1. Update the config.ini and configure to point to your MQTT broker and ET312 serial port.
2. Choose a topic, the script currently uses `#/channel_a` and `#/channel_b` to get values for setting the power levels.
3. Plug-in the ET312 as per the shockcade instructions. Configure to the maximum power levels you want to use.
2. Run the script using `python3 ./et312_mqtt.py`
3. If you don't have a source for the MQTT messages yet, try using `./generate_test_data` to generate some random changes every few seconds.

Some basic debug info is printed to the command line, but you should see your ET312 power levels change according to the values in the MQTT messages. Only the led's will reflect the power change, the power level reading on screen will continue to show the maximum power which will be used.

# Credits
https://github.com/buttshock/buttshock-py
