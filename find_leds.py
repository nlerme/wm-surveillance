#!/usr/bin/env python

# Packages
import cv2 as cv
import numpy as np
import os, time
import scipy.io as sio
from tkinter import messagebox as mb

#--- Functions ----------------------------------------------------------
def mouse_callback1( event, x, y, flags, params ):
	global leds_counter1, leds_counter2, leds_coords, img, nb_leds, roi_coords, led_radius, ending_led_index
	if (event==cv.EVENT_LBUTTONUP and leds_counter1<(nb_leds-1)) or (event==cv.EVENT_MBUTTONUP and ending_led_index<0):
		t = (int(x),int(y))
		leds_coords[:,leds_counter2] = t
		if event==cv.EVENT_LBUTTONUP:
			cv.circle(img, t, led_radius, (255,255,0), 2)
			leds_counter1 += 1
		else:
			cv.circle(img, t, led_radius, (255,0,255), 2)
			ending_led_index = leds_counter2
		if leds_counter2==(nb_leds-1):
			b = 0.5*(img.shape[0]+img.shape[1])*border_factor
			pmin = (int(np.min(leds_coords[0,:])-b),int(np.min(leds_coords[1,:])-b))
			pmax = (int(np.max(leds_coords[0,:]+b)),int(np.max(leds_coords[1,:]+b)))
			roi_coords[:,0] = pmin
			roi_coords[:,1] = pmax
			cv.rectangle(img, pmin, pmax, (0,255,255), 2)
		cv.imshow('image', img)
		leds_counter2 += 1

#--- Main ---------------------------------------------------------------
# Global variables
leds_fn = 'leds.mat'
nb_leds = 3
leds_coords = np.zeros((2,nb_leds),dtype=np.int)
roi_coords = np.zeros((2,2),dtype=np.int)
border_factor = 0.04
leds_counter1 = 0
leds_counter2 = 0
ending_led_index = -1

# We take a picture of the washing machine and load it
img_fn = '/tmp/img.jpg'
os.system('raspistill -o %s -v -q 100 -vs -ex night' % img_fn)
img = cv.imread(img_fn)
led_radius = max(1,int(0.005*img.shape[1]))

# We display the picture and keep track of leds positions
mb.showinfo('Information', 'Please click with left mouse button for marking ordinary leds and with middle button for ending led. Press escape key two times when finished.')
cv.namedWindow('image', cv.WINDOW_NORMAL)
cv.resizeWindow('image', int(img.shape[0]), int(img.shape[1]))
cv.setMouseCallback('image', mouse_callback1)
cv.imshow('image', img)
cv.waitKey(0)
if (leds_counter1!=(nb_leds-1) or ending_led_index<0):
	mb.showerror('Error', 'No enough ordinary leds marked or ending led not marked.')
	exit(0)

# We crop image, display it and ask for the ending led
img2 = img[roi_coords[1][0]:roi_coords[1][1],roi_coords[0][0]:roi_coords[0][1]]
cv.namedWindow('image', cv.WINDOW_NORMAL)
cv.resizeWindow('image', int(img2.shape[0]*3.0), int(img2.shape[1]*3.0))
cv.imshow('image', img2)
cv.waitKey(0)
cv.destroyAllWindows()

# We save normalized coordinates at MAT file
sio.savemat(leds_fn, {'led_radius':led_radius,'nb_leds':nb_leds,'border_factor':border_factor,'leds_coords':leds_coords,'roi_coords':roi_coords,'ending_led_index':ending_led_index})
