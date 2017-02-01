"""
generate_model_spectrum
=======================

This code generates a model spectrum based on emission-line fluxes and
expected ratios. 
"""

import sys, os

from chun_codes import systime

from os.path import exists
import commands
from astropy.io import ascii as asc
from astropy.io import fits

import numpy as np
import array, time, sets

import matplotlib.pyplot as plt

from astropy.table import Table

from locate_emission_lines import gaussian, gaussian_R

def main(tab0, R_spec=3000.0, silent=False, verbose=True):

    '''
    Main function() that generates a spectrum containing H-alpha, [NII],
    and [SII]

    Parameters
    ----------
    tab0 : astropy.table.table.Table
      Astropy table containing source ID, redshift, H-alpha flux, and NII/Ha
      flux ratio

    silent : boolean
      Turns off stdout messages. Default: False

    verbose : boolean
      Turns on additional stdout messages. Default: True
	  
    Returns
    -------

    Notes
    -----
    Created by Chun Ly, 1 February 2017
    '''
    
    if silent == False:
        print '### Begin generate_model_spectrum.main | '+systime()

    x_min, x_max = 6300.0, 7000.0 # in Angstroms
    x0 = np.arange(x_min, x_max, 0.25) # rest wavelength
    
    n_sources = len(tab0)

    s_lambda0 = ['Ha', 'NII', 'SII', 'SII']
    lambda0 = np.array([6562.8, 6583.6, 6716.42, 6730.78])

    ID0      = tab0['ID']
    zspec    = tab0['zspec']
    Ha_flux  = 10**(tab0['Ha_flux'])
    logNIIHa = tab0['logNIIHa']
    
    scale0 = [1.0, 0.0, 0.1, 0.1]
    
    for ii in range(n_sources):
        flux = np.zeros(len(x0))
        wave = (1+zspec[ii])*x0

        for ll in range(len(lambda0)):
            o_lambda = lambda0[ll] * (1+zspec[ii])
            
            s_temp = gaussian_R(wave, o_lambda, R_spec)
            if scale0[ll] != 0.0:
                flux += s_temp * Ha_flux * scale0[ll]
            else:
                flux += s_temp * Ha_flux * 10**(logNIIHa[ii])

        f_table = Table([wave, flux])

        outfile = ID0[ii]+'.spec.txt'
        if silent == False: print '### Writing : ', outfile
        asc.write(f_table, outfile, format='no_header')

    if silent == False:
        print '### End generate_model_spectrum.main | '+systime()
#enddef

