"""
find_nearby_bright_star
=======================

Search SDSS or 2MASS catalogs for nearest bright star as offset star
or to determine PA for longslit spectroscopy

Requirements:
 astroquery (https://astroquery.readthedocs.io/en/latest/)
 aplpy (https://aplpy.github.io/)

"""

import sys, os

from chun_codes import systime

from os.path import exists

from astropy.io import ascii as asc
from astropy.io import fits

import numpy as np

import matplotlib.pyplot as plt
import glob

import astropy.units as u
from astropy.table import Table, Column

from astropy import coordinates as coords
from astroquery.sdss import SDSS
from astroquery.irsa import Irsa as IRSA

import aplpy # + on 24/12/2016

from PyMontage.scripts import montage_reproj # + on 02/01/2017

# For SDSS only
SDSS_fld      = ['ra','dec','objid','run','rerun','camcol','field','obj',
                 'type','mode']
                 
SDSS_phot_fld = SDSS_fld + ['modelMag_u', 'modelMagErr_u', 'modelMag_g',
                            'modelMagErr_g', 'modelMag_r', 'modelMagErr_r',
                            'modelMag_i', 'modelMagErr_i', 'modelMag_z',
                            'modelMagErr_z']

def get_PA(c0, c1, silent=True, verbose=False):
    '''
    Function to determine the PA on the sky and central coordinates given
    two WCS coordinates

    Parameters
    ----------
    c0 : `astropy.coordinates` object
      Central coordinate of target

    c1 : `astropy.coordinates` object
      Central coordinate of nearby bright star

    silent : boolean
      Turns off stdout messages. Default: True

    verbose : boolean
      Turns on additional stdout messages. Default: False

    Returns
    -------
    PA : float
      Position angle between c0 and c1. Positive values is for East of North

    c_ctr : `astropy.coordinates` object
      Coordinate associated with center between target and nearby bright star

    Notes
    -----
    Created by Chun Ly, 3 January 2017
    '''
    
    if silent == False:
        print '### Begin find_nearby_bright_star.get_PA | '+systime()

    PA = c0.position_angle(c1).degree # + => East of North

    # Get central coordinate
    ra_avg  = np.average([c0.ra.value, c1.ra.value])
    dec_avg = np.average([c0.dec.value, c1.dec.value])

    c_ctr = coords.SkyCoord(ra=ra_avg, dec=dec_avg, unit=(u.degree,u.degree))

    if silent == False:
        print '### End find_nearby_bright_star.get_PA | '+systime()

    return PA, c_ctr
#enddef

def plot_finding_chart(fitsfile, t_ID, band0, c0, c1, out_pdf=None,
                       silent=True, verbose=False, catalog='SDSS'):
    '''
    Function to plot FITS images with WCS on the x- and y-axes

    Parameters
    ----------
    fitsfile : string
      Filename of FITS file

    t_ID : string
      Name of source

    band0 : string
      Observation waveband of image

    c0 : `astropy.coordinates` object
      Central coordinate of target

    c1 : `astropy.coordinates` object
      Central coordinate of nearby bright stars

    out_pdf : string
      Output PDF filename.
      Default: based on [fitsfile], replacing '.fits.gz' or '.fits' with '.pdf'

    silent : boolean
      Turns off stdout messages. Default: True

    verbose : boolean
      Turns on additional stdout messages. Default: False

    catalog : string
      Which survey (e.g., SDSS, 2MASS) the finding chart image is from.
      Default: 'SDSS'
	  
    Returns
    -------

    Notes
    -----
    Created by Chun Ly, 24 December 2016
    Modified by Chun Ly, 2 January 2017
     - Fix previous bug with show_markers (change facecolor)
     - Added input of c1 to indicate where bright alignment stars are
     - Added t_ID, band0 inputs for plt.annotate call
     - Changed out_pdf to keyword rather than input variable
     - Added catalog keyword
     - Change axis label values to clean it up
    '''

    # + on 02/01/2017
    if out_pdf == None:
        out_pdf = fitsfile.replace('.fits.gz', '.pdf').replace('.fits','.pdf')

    gc = aplpy.FITSFigure(fitsfile, figsize=(8,8), north=True)

    gc.show_grayscale(invert=True)
    gc.set_tick_color('black')

    # + on 02/01/2017 to fix plotting
    gc.set_tick_yspacing('auto')
    gc.ticks.set_yspacing(5/60.0) # Every 5 arcmin in Dec
    gc.set_tick_labels_format(xformat='hh:mm:ss', yformat='dd:mm')
    
    # Fix bug. marker='+' won't work with facecolor='none'
    gc.show_markers([c0.ra.value], [c0.dec.value], layer='primary',
                    edgecolor='red', facecolor='red', marker='+', s=25)

    # + on 02/01/2017
    gc.show_markers([c1.ra.value], [c1.dec.value], layer='secondary',
                    edgecolor='blue', facecolor='none', marker='o', s=25,
                    linewidth=0.5)

    # + on 02/01/2017
    lab0 = t_ID+'\n'+catalog+' '+band0
    gc.add_label(0.03, 0.95, lab0, relative=True, ha='left', va='top',
                 weight='bold', size='large')

    gc.savefig(out_pdf)
#enddef

def get_sdss_images(c0, out_fits, band=u'i', silent=True, verbose=False):
    '''
    Function to grab SDSS FITS image that is associated with the provided
    coordinate

    Parameters
    ----------
    c0 : str or `astropy.coordinates` object
      The target around which to search. It may be specified as a string
      in which case it is resolved using online services or as the
      appropriate `astropy.coordinates` object. ICRS coordinates may also
      be entered as strings as specified in the `astropy.coordinates`
      module.

    band : string
      Filter name for image to obtain from query (e.g., 'u', 'g', 'r', 'i', 'z')
      Default: 'i'

    catalog : string
      Either SDSS or '2MASS'. Default: 'SDSS'
    
    format : string
      Format of infile ASCII file. Default: "commented_header"

    silent : boolean
      Turns off stdout messages. Default: True

    verbose : boolean
      Turns on additional stdout messages. Default: False
	  
    Returns
    -------

    Notes
    -----
    Created by Chun Ly, 24 December 2016
    '''

    imgs = SDSS.get_images(coordinates=c0, radius=1*u.arcmin, band=band,
                           timeout=180)

    n_frames = len(imgs)

    if silent == False: print '### Writing : ', out_fits
    for ff in range(n_frames):
        t_hdu = imgs[ff][0]
        if ff == 0:
            t_hdu.writeto(out_fits, clobber=True)
        else:
            fits.append(out_fits, t_hdu.data, t_hdu.header)
    return t_hdu
#enddef

def main(infile, out_path, finding_chart_path, finding_chart_fits_path,
         max_radius=60*u.arcsec, mag_limit=20.0, mag_filt='modelMag_i',
         catalog='SDSS', format='commented_header', silent=False, verbose=True):

    '''
    Main function to find nearby star

    Parameters
    ----------
    infile : string
      Filename for ASCII file that contains ID, RA, and DEC
      RA and DEC must be provided in sexigesimal format.
      The columns should be referred to as 'ID', 'RA', and 'DEC'

    out_path : string
      Full path to output ASCII tables. Must end with a '/'

    finding_chart_path : string
      Full path for outputted PDF finding charts. Must end with a '/'

    finding_chart_fits_path : string
      Full path for outputted finding charts. Must end with a '/'

    max_radius : float
      Maximum radius. Provide with astropy.units for arcsec,
      arcmin, or degrees. Default: 60 * u.arcsec

    mag_limit : float
      Faintest source to consider in AB mag. Default: 20.0 mag

    mag_filt : string
      The name of the filter adopt the above [mag_limit]
      Default: 'modelMag_i'

    catalog : string
      Either SDSS or '2MASS'. Default: 'SDSS'
    
    format : string
      Format of infile ASCII file. Default: "commented_header"

    silent : boolean
      Turns off stdout messages. Default: False

    verbose : boolean
      Turns on additional stdout messages. Default: True
	  
    Returns
    -------

    Notes
    -----
    Created by Chun Ly, 23 December 2016
    Modified by Chun Ly, 24 December 2016
     - Added query for 2MASS
     - Keep those with mode = 1 (Primary sources only, reduces duplication)
    Modified by Chun Ly, 02 January 2017
     - if statement if [good] is empty
     - Added different path for FITS finding chart [finding_chart_fits_path]
    '''

    if silent == False:
        print '### Begin find_nearby_bright_star.main | '+systime()

    if silent == False: print '### Reading : ', infile
    data0 = asc.read(infile)

    ID  = data0['ID'].data
    RA  = data0['RA'].data
    DEC = data0['DEC'].data
    n_sources = len(ID)

    ID0 = [ss.replace('*','') for ss in ID] # Clean things up 24/12/2016

    if silent == False:
        print '## Search criteria : '
        print '## max_radius(arcsec) : ', max_radius.to(u.arcsec).value
        print '## mag_limit : ', mag_limit
        print '## filter selection : ', mag_filt
    
    for ii in range(n_sources):
        c0 = coords.SkyCoord(ra=RA[ii], dec=DEC[ii], unit=(u.hour, u.degree))
        if catalog == 'SDSS':
            xid = SDSS.query_region(c0, max_radius, data_release=12,
                                    photoobj_fields=SDSS_phot_fld)

            # Keep stars only (type == 6)
            # http://www.sdss.org/dr12/algorithms/classify/#photo_class
            # Keep primary target to deal with duplicate entries | 24/12/2016
            # Avoid unusual mag values | Mod on 24/12/2016
            good = np.where((xid[mag_filt] <= mag_limit) &
                            (xid[mag_filt] != -9999.0) & # Mod on 24/12/2016
                            (xid['type'] == 6) & (xid['mode'] == 1))[0]
            # Moved up on 24/12/2016
            out_table_file = out_path + ID0[ii] + '.SDSS.nearby.txt'
            
        # + on 24/12/2016
        if catalog == '2MASS':
            xid = IRSA.query_region(c0, catalog='fp_psc', radius=max_radius)
            good = np.where(xid[mag_filt] <= mag_limit)[0]
            out_table_file = out_path + ID0[ii] + '.2MASS.nearby.txt'

        if silent == False:
            print '## Finding nearby stars for '+ID[ii]+'. '+\
                str(len(good))+' found.'
            if len(good) == 0: print '## Skipping ahead.'
        
        # Mod on 02/01/2017 to handle python crash when [good] is empty
        if len(good) > 0:
            xid = xid[good]

            # Get distance from target
            c1 = coords.SkyCoord(xid['ra'], xid['dec'], unit=(u.degree, u.degree))
            sep = c0.separation(c1).to(u.arcsec).value
            col1 = Column(sep, name='Dist(arcsec)')
            xid.add_column(col1)

            # Sort by distance and then brightness
            xid.sort(['Dist(arcsec)',mag_filt])
        
            if silent == False:
                print '### Writing: ', out_table_file
                asc.write(xid, out_table_file, format='fixed_width_two_line')
        
            if catalog == 'SDSS':
                out_fits = finding_chart_fits_path + ID0[ii]+'.SDSS.fits.gz'
                out_pdf  = finding_chart_path + ID0[ii]+'.SDSS.pdf'
                print out_fits
                band0 = mag_filt.replace('modelMag_','') # + on 02/01/2017
                if not exists(out_fits):
                    t_hdu = get_sdss_images(c0, out_fits, band=band0)
                else:
                    t_hdu = fits.open(out_fits)

            # Mod on 02/01/2017 for inputs
            if catalog == 'SDSS':
                plot_finding_chart(out_fits, ID0[ii], band0, c0, c1,
                                   catalog=catalog, out_pdf=out_pdf)
        #endif
    #endfor
        
    if silent == False:
        print '### End find_nearby_bright_star.main | '+systime()
#enddef

def zcalbase_gal_gemini():
    '''
    Function to run find_nearby_bright_star.main() but for Gemini-N/GNIRS
    targets

    Parameters
    ----------
    None
          
    Returns
    -------
    
    Notes
    -----
    Created by Chun Ly, 23 December 2016
    Modified by Chun Ly, 24 December 2016
     - Added call to main() using 2MASS selection
     - Change max_radius from 5 arcmin to 120 arcsec.
       Slit length of GNIRS is 99 arcsec. Will do offset star if too far away
    Modified by Chun Ly, 2 January 2017
     - Two separate paths for finding chart FITS and PDF
    '''

    path0                   = '/Users/cly/Dropbox/Observing/2017A/Gemini/'
    infile                  = path0 + 'targets.txt'
    out_path                = path0 + 'Alignment_Stars/'
    finding_chart_path      = path0 + 'Finding_Charts/'

    # + on 02/01/2017
    finding_chart_fits_path = '/Users/cly/data/Observing/Gemini/Finding_Charts/'

    max_radius = 120 * u.arcsec

    # Select alignment stars based on SDSS
    main(infile, out_path, finding_chart_path, finding_chart_fits_path,
         max_radius=max_radius, mag_limit=19.0, catalog='SDSS')

    # Select alignment stars based on 2MASS
    # + on 24/12/2016
    main(infile, out_path, finding_chart_path, finding_chart_fits_path,
         max_radius=max_radius, mag_limit=17.0, catalog='2MASS', mag_filt='j_m')

