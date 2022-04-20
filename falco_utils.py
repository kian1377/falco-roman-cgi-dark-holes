import numpy as np
import pickle
from pathlib import Path
from astropy.io import fits
from tabulate import tabulate
from matplotlib.patches import Circle

import proper
import roman_phasec_proper as phasec

output_dir = Path('/home/u21/kianmilani/src/pyfalco/data/brief/')

flatmaps_dir = Path('/home/u21/kianmilani/Documents/falco-roman-cgi-dark-holes/flatmaps')
dm1_flatmap = fits.getdata(flatmaps_dir/'dm1_m_flat_hlc_band1.fits')
dm2_flatmap = fits.getdata(flatmaps_dir/'dm2_m_flat_hlc_band1.fits')
dm1_design = fits.getdata(flatmaps_dir/'dm1_m_design_hlc_band1.fits')
dm2_design = fits.getdata(flatmaps_dir/'dm2_m_design_hlc_band1.fits')
dm1_total = dm1_flatmap + dm1_design
dm2_total = dm2_flatmap + dm2_design

dm1_best = proper.prop_fits_read( phasec.lib_dir + r'/examples/hlc_best_contrast_dm1.fits' )
dm2_best = proper.prop_fits_read( phasec.lib_dir + r'/examples/hlc_best_contrast_dm2.fits' )

def create_annular_mask(params, mp, npsf):
    xfp = np.linspace(-0.5, 0.5, npsf) * npsf * mp.full.final_sampling_lam0
    x,y = np.meshgrid(xfp,xfp)
    
    r = np.hypot(x, y)
    mask = (r < params['outer_radius']) * (r > params['inner_radius'])
    if params['direction'] == 'r': mask *= (x > params['edge_position'])
    elif params['direction'] == 'l': mask *= (x < -params['edge_position'])
    elif params['direction'] == 't': mask *= (y > params['edge_position'])
    elif params['direction'] == 'b': mask *= (y < -params['edge_position'])
    
    return mask

def create_circ_patches(circ_params):
    circ_patches = [Circle( (0,0), circ_params['inner_radius'], color='c', fill=False), 
                  Circle( (0,0), circ_params['outer_radius'], color='c', fill=False)]
    return circ_patches

def zone_table(zone_radii, zone_contrasts):
    rows = []
    for i in range(len(zone_radii)-1):
        rows.append([i, zone_radii[i], zone_radii[i+1], zone_contrasts[i]])

    print(tabulate(rows, numalign='right', stralign='center', tablefmt='fancy_grid', floatfmt=['', '.1f', '.1f', '.3e'],
                   headers=['Zone', 'Inner Radius', 'Outer Radius', 'Zone Avg Contrast']) )


# functions for saving python data
def save_pickle(fname, data, quiet=False):
    out = open(str(output_dir/fname), 'wb')
    pickle.dump(data, out)
    out.close()
    if not quiet: print('Saved data to: ', str(output_dir/fname))

def load_pickle(fname):
    infile = open(str(output_dir/fname),'rb')
    pkl_data = pickle.load(infile)
    infile.close()
    return pkl_data    
    
