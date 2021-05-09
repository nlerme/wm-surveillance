#!/bin/bash

id=$(ps -ef | grep "[w]atch_leds.py" | awk '{print $2}')
sudo kill -9 ${id}
