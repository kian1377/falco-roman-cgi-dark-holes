import numpy as np
from astropy.io import fits
import os
from pathlib import Path
import copy
import shutil
from importlib import reload

import matplotlib.pyplot as plt

import falco
import proper

import misc

import hlc_band1_custom_config as config
reload(config)

output_dir = Path('/home/u21/kianmilani/src/pyfalco/data/brief/')

flatmaps_dir = Path('/home/u21/kianmilani/Documents/falco-roman-cgi-dark-holes/flatmaps')
dm1_design = fits.getdata(flatmaps_dir/'dm1_m_design_hlc_band1.fits')
dm2_design = fits.getdata(flatmaps_dir/'dm2_m_design_hlc_band1.fits')
dm1_flatmap = fits.getdata(flatmaps_dir/'dm1_m_flat_hlc_band1.fits')
dm2_flatmap = fits.getdata(flatmaps_dir/'dm2_m_flat_hlc_band1.fits')

# Setup model parameters
mp = config.setup(N_subpass=1, N_waves_per_subpass=1, fractional_bandwidth=0.01,
                  estimator='perfect', 
                  N_iterations=5,
                  spatial_weighting=[],
                  dark_hole_sides='r',
                  dm1_initial=dm1_flatmap, dm2_initial=dm2_flatmap,
#                   dm1_initial=dm1_flatmap+dm1_design, dm2_initial=dm2_flatmap+dm2_design,
                  label='hlc_band1_perfect_bw0.1_r_flatmap')

misc.myimshow2(mp.full.dm1.flatmap, mp.full.dm2.flatmap)

# Perform phase retrieval
config.perform_phase_retrieval(mp, quiet=True)

# Setup the workspace
out = falco.setup.flesh_out_workspace(mp)

# Run the WFSC loop
falco.wfsc.loop(mp, out)







