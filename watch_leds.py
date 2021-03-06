#!/usr/bin/env python

#--- Packages ------------------------------------------------------------
import cv2 as cv
import numpy as np
import scipy.io as sio
import os, time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pushbullet import PushBullet

#--- Functions -------------------------------------------------------------
def send_email( src_mail, dst_mail, subject, msg_str, pwd, server_name, server_port ):
	msg = MIMEMultipart()
	msg['From'] = src_mail
	msg['To'] = dst_mail
	msg['Subject'] = subject
	msg.attach(MIMEText(msg_str))
	mailserver = smtplib.SMTP(server_name, server_port)
	mailserver.ehlo()
	mailserver.starttls()
	mailserver.ehlo()
	mailserver.login(src_mail, pwd)
	mailserver.sendmail(src_mail, dst_mail, msg.as_string())
	mailserver.quit()

def take_picture( img_fn ):
	os.system('raspistill -o %s -q 100 -vs -ex auto -mm average -awb auto' % img_fn)
	return cv.imread(img_fn, 0)

def process_image( img_fn, img, det_threshold, nb_leds, leds_coords, roi_coords, debug ):
	# We crop the image
	img = img[roi_coords[1,0]:roi_coords[1,1],roi_coords[0,0]:roi_coords[0,1]]
	if debug:
		cv.imwrite('%s_step0.jpg'%os.path.splitext(img_fn)[0], img)

	# We apply a denoising filter
	sigma = 5       # filter strength
	template_ws = 7 # template window size
	search_ws = 21  # search window size
	img_d = cv.fastNlMeansDenoising(img, None, sigma, template_ws, search_ws)
	if debug:
		cv.imwrite('%s_step1.jpg'%os.path.splitext(img_fn)[0], img_d)

	# We apply a closing operator
	size = max(1,int(0.15*img_d.shape[1]))
	kernel = np.ones((size,size),np.uint8)
	img_closing = cv.morphologyEx(img_d, cv.MORPH_CLOSE, kernel)
	if debug:
		cv.imwrite('%s_step2.jpg'%os.path.splitext(img_fn)[0], img_closing)

	# We construct a prior image on leds locations
	img_lps = np.zeros(img.shape, dtype=np.float)
	for k in range(nb_leds):
		x = leds_coords[0,k]
		y = leds_coords[1,k]
		img_ll = np.zeros(img.shape, dtype=np.float)
		img_ll[y,x] = 1.0
		sigma = (img.shape[1]*0.055)
		img_lp = cv.GaussianBlur(img_ll, (0,0), sigma)
		img_lp = img_lp/np.max(img_lp)
		img_lps = np.maximum(img_lps,img_lp)
	if debug:
		cv.imwrite('%s_step3.jpg'%os.path.splitext(img_fn)[0], np.uint8(255.0*img_lps))

	# We construct a prior on bright image intensities
	sigma = 0.2
	img_ips = np.exp(-0.5*(np.square((img_closing/255.0)-1.0)/sigma**2))
	if debug:
		cv.imwrite('%s_step4.jpg'%os.path.splitext(img_fn)[0], np.uint8(255.0*img_ips))

	# We multiply both images and apply a closing operator
	img_m = np.uint8(255.0*np.multiply(img_ips,img_lps))
	size = max(1,int(0.014*img_d.shape[1]))
	kernel = np.ones((size,size),np.uint8)
	img_m = cv.morphologyEx(img_m, cv.MORPH_CLOSE, kernel)
	if debug:
		cv.imwrite('%s_step5.jpg'%os.path.splitext(img_fn)[0], img_m)

	# We threshold the resulting image
	ret,img_th = cv.threshold(img_m, int(det_threshold*255), 255, cv.THRESH_BINARY)
	if debug:
		cv.imwrite('%s_step6.jpg'%os.path.splitext(img_fn)[0], img_th)

	# We label connected components and return centroids
	out = cv.connectedComponentsWithStats(img_th, 8, cv.CV_32S)
	centroids = out[3]
	return centroids

def send_push_bullet_msg( api_key, subject, msg ):
	pb = PushBullet(api_key)
	pb.push_note(subject, msg)

#--- Main ------------------------------------------------------------------
# Global variables
leds_fn                    = 'leds.mat'                           # Filename of MAT file containing information about leds (string)
det_threshold              = 0.5                                  # Detection threshold (in [0,1])
sleeping_time              = 30                                   # Sleeping time between two successive acquisitions (>0; in seconds)
nb_required_no_leds_det    = 5                                    # Number of no leds detections (>0)
nb_required_ending_led_det = 5                                    # Number of ending led detections (>0)
debug                      = True                                 # Debug flag (True or False)
img_fn                     = '/tmp/img.jpg'                       # Image filename (string)
email_dst                  = 'my_email@fai.com'                   # Email recipient
email_src                  = 'my_email@fai.com'                   # Email sender
email_subject              = 'Machine ?? laver'                    # Email subject
email_password             = 'my_password'                        # Email password
email_server_name          = 'my_server'                          # Email server name
email_server_port          = 0                                    # Email server port
push_bullet_api_key        = 'my_api_key'                         # PushBullet api key (from pushbullet.com account)
push_bullet_subject        = email_subject                        # PushBullet subject

# We load information about leds
r                = sio.loadmat(leds_fn)
nb_leds          = int(r['nb_leds'])
leds_coords      = r['leds_coords']
roi_coords       = r['roi_coords']
led_radius       = r['led_radius']
ending_led_index = int(r['ending_led_index'])

# We express leds positions w.r.t. roi frame
leds_coords[0,:] = leds_coords[0,:]-roi_coords[0][0]
leds_coords[1,:] = leds_coords[1,:]-roi_coords[1][0]

# We display some info
print('------------------------------------------------')
print('+ opencv version: %s'%cv.__version__)
print('+ led radius: %d'%led_radius)
print('+ nb leds: %d'%nb_leds)
print('+ ending led index: %d'%ending_led_index)
print('+ leds coords:')
for k in range(nb_leds):
	print('  + led %d: (x=%d,y=%d)'%(k,leds_coords[0,k],leds_coords[1,k]))
print('+ roi coords: (xmin=%d,xmax=%d,ymin=%d,ymax=%d)'%(roi_coords[0,0],roi_coords[0,1],roi_coords[1,0],roi_coords[1,1]))
print('------------------------------------------------')

# We loop until washing machine program ends
count             = 0
nb_no_leds_det    = 0
nb_ending_led_det = 0
total_time        = 0

while nb_ending_led_det<nb_required_ending_led_det and nb_no_leds_det<nb_required_no_leds_det:
	# We take a picture of the leds on the washing machine
	img = take_picture(img_fn)

	# We process the acquired image and get the location of leds
	centroids = process_image(img_fn, img, det_threshold, nb_leds, leds_coords, roi_coords, debug)

	# We take decision w.r.t. centroids
	if len(centroids)==1:
		print('+ image %d -> no leds detected'%count)
		nb_no_leds_det += 1
	elif len(centroids)==2:
		xn = centroids[1,0]/img.shape[1]
		xs = np.sort(leds_coords[0,:])
		xs2 = np.zeros(len(xs)-1,dtype=np.float)

		for k in range(len(xs2)):
			xs2[k] = (0.5*(xs[k]+xs[k+1]))/img.shape[1]

		xs2 = np.concatenate(([0.0],xs2,[1.0]))
		index = -1

		for k in range(len(xs2)-1):
			if xn>xs2[k] and xn<=xs2[k+1]:
				print('+ image %d -> state %d (%f,%f)'%(count,k,centroids[1,0],xn))
				index = k

		if index==ending_led_index:
			nb_ending_led_det += 1
	else:
		print('+ image %d -> %d leds detected'%(count,len(centroids)))

	# We sleep for a while
	time.sleep(sleeping_time)

	count += 1
	total_time += sleeping_time

print('------------------------------------------------')

# If the number of ending led detections is enough, we send an e-mail
if nb_ending_led_det==nb_required_ending_led_det:
	msg = 'Cycle termin?? en %s !'%timedelta(seconds=int(total_time))
	print('+ sending email')
	send_email(email_dst, email_src, email_subject, msg, email_password, email_server_name, email_server_port)
	print('+ sending push bullet message')
	send_push_bullet_msg(push_bullet_api_key, push_bullet_subject, msg)

# In any case, we power off the pi
print('+ shutting down')
while True:
	os.system('sudo softshutdown.sh 1')
	time.sleep(10)
