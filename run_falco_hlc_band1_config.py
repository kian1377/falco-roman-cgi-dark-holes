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

import falco_utils as fu
import falco_hlc_band1_setup_config as config
reload(config)
reload(fu)

mp = config.setup(N_subpass=1, N_waves_per_subpass=1, fractional_bandwidth=0.01,
                  estimator='pwp-bp', 
                  N_iterations=10,
                  spatial_weighting=[],
                  dark_hole_sides='lr',
                  dm1_initial=fu.dm1_best, dm2_initial=fu.dm2_best)

mp.runLabel = 'hlc_band1_best_' + mp.estimator + '_bw{:.2f}_'.format(mp.fracBW) \
              + mp.Fend.sides + '_{:d}itr'.format(mp.Nitr) + '_v1'
print(mp.runLabel)
print()

# Perfrom phase retrieval
config.perform_phase_retrieval(mp, quiet=True)

# Setup the workspace
out = falco.setup.flesh_out_workspace(mp)

# Run the WFSC loop
falco.wfsc.loop(mp, out)

# Save the model parameters
fu.save_pickle(mp.runLabel, mp)







