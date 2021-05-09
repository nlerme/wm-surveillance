Presentation
------------
wm-surveillance is a python program for automatically detecting end of washing machine program. This software intended to be used to be typically installed on top of a washing machine and run on an embedded device (such as Raspberry pi) equipped of an infrared high resolution color camera. The end of the washing program is detected by observing the state of the leds of the washing machine and the user is informed via email and pushbullet notification. The detection relies on image processing algorithm that are robust to luminosity/contrast changes and vibrations. The detection algorithms assume that the leds are brighter than the sheet metal of the mashing machine and the amount of vibrations remains small.

Running
-------
1. Firstly, the position of the leds must be interactively indicated by the user using "find_leds.py". Currently, this operation must be run each time that the washing machine is moved.
2. Secondly, the detection of the end of the washing machine program can be run using "watch_leds.py".
