"""
This file is meant to be used as a module for the ExoCTK website i.e. 
app_exoctk.py. It is part of the ExoCTK package. It contains a single 
function that queries irsa to get nearby sources using 2MASS catalog, 
utilizes phoenix models and returns a fits file that contains overlap 
estimations.

Authors:
	Rafia Bushra, University of Arizona
	
	Jonathan Fraine, Space Telescope Science Institute
	
	David Lafreniere, University de Montreal

Usage:
	* From python script:
		from ExoCTK.tor.tor2.sossFieldSim import sossFieldSim
		sossFieldSim(ra, dec, binComp, dir)
		
	* From terminal:
		cd into ExoCTK/ExoCTK/tor/tor2 directory
		$ python runSossFieldSim.py ra dec dir binComp 
		
	
Requirements:
	* ExoCTK package must be installed
	* There must be an "idlSaveFiles" folder in ExoCTK.data.tor
"""


from astroquery.irsa import Irsa
from astropy.io import fits
import matplotlib.pyplot as plt
import astropy.coordinates as crd
import astropy.units as u
import numpy as np
import os
import glob
import idlsave
import ExoCTK

def sossFieldSim(ra, dec, dir = '.', binComp=None):
	"""
	The only function of this module. Runs simulation and calculates 
	spectral overlap.
	
	Args:
		ra (str)       : Right Ascension of target in hh:mm:ss
		dec (str)      : Declination of target in ddd:mm:ss
		dir (str)      : dirctory path of where the fits file should be 	
						 saved
		binComp (list) : [deltaRA,deltaDEC,J,H,K] of binary companion
		
	
	Returns:
		cubeName (str) : Name of the fits file this function creates 	
						 (includes file path), so you can call for the 
						 fits file from a python script or terminal
	"""

	if binComp == '':
		binComp = None

	# stars in large field around target
	targetcrd = crd.SkyCoord(ra = ra, dec = dec, unit=(u.hour, u.deg))
	targetRA = targetcrd.ra.value
	targetDEC = targetcrd.dec.value
	info   = Irsa.query_region(targetcrd, radius = 2.5*u.arcmin, catalog = 'fp_psc')
	# coordinates of possible contaminants in degrees
	contamRA   = info['ra'].data.data 
	contamDEC  = info['dec'].data.data
	Jmag        = info['j_m'].data.data
	Hmag        = info['h_m'].data.data
	Kmag        = info['k_m'].data.data
	J_Hobs      = (Jmag-Hmag)
	H_Kobs      = (Hmag-Kmag)
	
	# target coords
	distance    = np.sqrt((targetRA-contamRA)**2 + (targetDEC-contamDEC)**2)
	targetIndex = np.argmin(distance) # the target
	
	# add any missing binary companion
	cubeNameSuf=''
	if binComp is not None:
		deg2rad = np.pi/180
		contamRA    = np.append(contamRA, (contamRA[targetIndex] + binComp[0]/3600/cos(contamDEC[targetIndex]*deg2rad)))
		contamDEC   = np.append(contamDEC, (contamDEC[targetIndex] + binComp[1]/3600))
		Jmag        = np.append(Jmag,binComp[2])
		Hmag        = np.append(Kmag,binComp[3])
		Kmag        = np.append(Kmag,binComp[4])
		J_Hobs      = (Jmag-Hmag)
		H_Kobs      = (Hmag-Kmag)
		cubeNameSuf ='_custom'
	

	#Joe's coordinate conversion code
	def deg2HMS(ra='', dec='', round=False):
		RA, DEC, rs, ds = '', '', '', ''
		if dec:
			if str(dec)[0] == '-':
		  		ds, dec = '-', abs(dec)
			deg = int(dec)
			decM = abs(int((dec-deg)*60))
			if round:
		  		decS = int((abs((dec-deg)*60)-decM)*60)
			else:
		  		decS = (abs((dec-deg)*60)-decM)*60
			DEC = '{0}{1} {2} {3}'.format(ds, deg, decM, decS)

		if ra:
			if str(ra)[0] == '-':
		  		rs, ra = '-', abs(ra)
			raH = int(ra/15)
			raM = int(((ra/15)-raH)*60)
			if round:
		  		raS = int(((((ra/15)-raH)*60)-raM)*60)
			else:
		  		raS = ((((ra/15)-raH)*60)-raM)*60
			RA = '{0}{1} {2} {3}'.format(rs, raH, raM, raS)

		if ra and dec:
			return (RA, DEC)
		else:
			return RA or DEC
			
			

	cubeName = dir+'/cube_RA_' + deg2HMS(ra = contamRA[targetIndex], round = True).replace(' ',':') + '_DEC_' + deg2HMS(ra = contamDEC[targetIndex], round = True).replace(' ',':') + cubeNameSuf + '.fits'

	print('Cube name:')
	print(cubeName)
	print('cubNameSuf:')
	print(cubeNameSuf)
	print('Target coordinates:')
	print(deg2HMS(ra = contamRA[targetIndex]))
	print(deg2HMS(dec = contamDEC[targetIndex]))


	if os.path.exists(cubeName) and (binComp is not None):
		return

	
	#Restoring model parameters
	modelParam = idlsave.read(os.path.join(os.path.dirname(ExoCTK.__file__),'data/tor/idlSaveFiles/modelsInfo.sav')) 
	models     = modelParam['models']
	modelPadX  = modelParam['modelpadx']
	modelPadY  = modelParam['modelpady'] 
	dimXmod    = modelParam['dimxmod']
	dimYmod    = modelParam['dimymod']
	jhMod      = modelParam['jhmod']
	hkMod      = modelParam['hkmod']
	teffMod    = modelParam['teffmod'] 
	

	# Initialize final fits cube that contains the modelled traces with contamination
	PAmin = 0
	PAmax = 360
	angle_step = 1	# degrees
	# Set of fov angles to cover
	angle_set = np.arange(PAmin, PAmax, angle_step)	# degrees  the upper limit
	nsteps    = len(angle_set)
	simucube  = np.zeros([nsteps+2,2048, 256])  # cube of trace simulation at every degree of field rotation,+target at O1 and O2

	niriss_pixel_scale = 0.065	# arcsec

	sweetspot = dict(x=99.9,y=99.9,contamRA=99.9,contamDEC=99.9,jmag=99.9)
	sweetspot['x'] = 859			# position on the detector of the target in direct images
	sweetspot['y'] = 107
	sweetspot['contamRA'] = contamRA[targetIndex]
	sweetspot['contamDEC'] = contamDEC[targetIndex]
	sweetspot['jmag'] = Jmag[targetIndex]
	

	# Put field stars position and magnitudes in a dictionary
	nstars = len(contamRA)
	stars = dict(x=np.empty(nstars), y=np.empty(nstars), contamRA=np.empty(nstars), contamDEC=np.empty(nstars), jmag=np.empty(nstars))
	
	stars['contamRA']  = contamRA
	stars['contamDEC'] = contamDEC
	stars['jmag'] = Jmag

	# find Teff of each star
	T = np.zeros(nstars)
	for j in range(nstars):
		color_seperation = (J_Hobs[j]-jhMod)**2+(H_Kobs[j]-hkMod)**2
		min_seperation_ind = np.argmin(color_seperation)
		T[j]=teffMod[min_seperation_ind]

	# load colors
	# Big loop to generate a simulation at each Field-of-view (FOV) rotation
	radeg = 180/np.pi
	saveFiles = glob.glob(os.path.join(os.path.dirname(ExoCTK.__file__),'data/tor/idlSaveFiles/*.sav'))[:-1]
	
	for angle in range(angle_set.size): 
		fieldrotation = angle_set[angle]

		pixelsep = 3600 * np.sqrt(((np.cos(sweetspot['contamDEC']/radeg)*(stars['contamRA'] - sweetspot['contamRA']))**2) +((stars['contamDEC'] - sweetspot['contamDEC'])**2))
		xo = -np.cos(sweetspot['contamDEC']/radeg)*(stars['contamRA'] - sweetspot['contamRA'])*3600/niriss_pixel_scale
		yo = (stars['contamDEC'] - sweetspot['contamDEC'])*3600/niriss_pixel_scale

		dx = xo * np.cos(fieldrotation/radeg) - yo * np.sin(fieldrotation/radeg)
		dy = xo * np.sin(fieldrotation/radeg) + yo * np.cos(fieldrotation/radeg)
	
		stars['x'] = dx+sweetspot['x']
		stars['y'] = dy+sweetspot['y']
 
	
		# Retain stars that are within the Direct Image NIRISS POM FOV
		
		ind = np.where((stars['x'] >= -162) & (stars['x'] <= 2047+185) & (stars['y'] >= -154) & (stars['y'] <= 2047+174))[0]
		starsInFOV = dict(x=stars['x'][ind], y =stars['y'][ind], contamRA=stars['contamRA'][ind], contamDEC=stars['contamDEC'][ind], jmag=stars['jmag'][ind]) # *** pour In Field Of View
		dx = dx[ind]
		dy = dy[ind]
		T_loop = T[ind]
		

		if 0 & nstars > 1:
			# Display the star field and sub array location in red
			plt.plot(starsInFOV['x'], starsInFOV['y'], 'o')
			plt.xlim(-50,2047+50)
			plt.ylim(-50,2047+50)
			plt.plot([0,2047,2047,0,0],[0,0,2047,2047,0], 'r')
			plt.plot([0,255,255,0,0],[0,0,2047,2047,0], 'g')
			plt.plot(sweetspot['x'], sweetspot['y'], 'ro')
			plt.show()

		for i in range(len(ind)):
			intx = round(dx[i])
			inty = round(dy[i])
			# print(intx,inty)

			k=np.where(teffMod == T_loop[i])
			k = k[0][0]
			
			
			fluxscale = 10.0**(-0.4*(starsInFOV['jmag'][i] - sweetspot['jmag']))

			# if target and first angle, add target traces of order 1 and 2 in output cube
			if (intx == 0) & (inty == 0) & (angle == 0):
				
				
				fNameModO12 = saveFiles[k]
				modelO12 = idlsave.read(fNameModO12)['modelo12']
				simucube[0, :, :]= modelO12[0, modelPadY:modelPadY+2048, modelPadX:modelPadX+256] * fluxscale # order 1
				simucube[1, :, :]= modelO12[1, modelPadY:modelPadY+2048, modelPadX:modelPadX+256] * fluxscale # order 2
		
			# if a field star
			
			if (intx != 0) or (inty != 0):
				mx0=int(modelPadX-intx)
				mx1=int(modelPadX-intx+256)
				my0=int(modelPadY-inty)
				my1=int(modelPadY-inty+2048)
				
				if (mx0 > dimXmod) or (my0 > dimYmod): #removed the -1 here
					continue
				if (mx1 < 0) or (my1 < 0):
					continue
				
				x0  =(mx0<0)*(-mx0) 
				y0  =(my0<0)*(-my0) 
				mx0 *=(mx0 >= 0)  
				mx1 = dimXmod if mx1>dimXmod else mx1 
				my0 *=(my0 >= 0)  
				my1 =dimYmod if my1>dimYmod else my1 


				simucube[angle+2, y0:y0+my1-my0, x0:x0+mx1-mx0] += models[k, my0:my1, mx0:mx1] * fluxscale
	
	fits.writeto(cubeName, simucube, overwrite = True)
	
	return cubeName