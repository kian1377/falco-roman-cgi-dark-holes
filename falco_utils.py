import numpy as np

from tabulate import tabulate
from matplotlib.patches import Circle

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

