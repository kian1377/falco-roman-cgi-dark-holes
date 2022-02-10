import numpy as np
import os
from pathlib import Path
import copy

from astropy.io import fits
import matplotlib.pyplot as plt

import falco
import proper
import roman_phasec_proper as phasec

''' 
This file initializes the model parameters (mp) of the coronoagrpah configuration to perform 
the WFSC loop over. Not all settings of the model parameters are set here. Only the basic 
settings that are not altered regularly such as basic system and DM information. 
'''

def setup(N_subpass=1, N_waves_per_subpass=1, fractional_bandwidth=0.01, # for a quick run
          pol_conditions=[10], polaxis=10,
          estimator='perfect',
          N_iterations=5,
          spatial_weighting=[], 
          dark_hole_sides='lr',
          label='hlc_band1_config',
          dm1_initial=np.zeros((48,48)), dm2_initial=np.zeros((48,48)),
          plot_outputs=True, use_parallel=False, N_threads=8, # computational settings
         ):
    
    '''
    kwarg descriptions:
        N_subpass: integer
            Number of sub-bandpasses to use
        N_waves_per_subpass: integer
            Number of wavelengths per sub-bandpass to approximate image of a sub-bandpass
        fractional_bandwidth: float
            Overall bandwidth of the instrument
        pol_conditions: list
            Which polarization states to use when creating an image.
        polaxis: integer
            Polarization state to use when making a single call to the Roman CGI PROPER model.
        estimator: string
            Either 'perfect' or 'pwp-bp', pwp-bp will use pair-wise probing batch-process to estimate E-Field
        N_iterations: integer
            How many iterations to run WFSC loop for
        spatial_weighting: list, [[inner radius, outer radius, intensity weight], (as many rows as desired)], 
            Spatial control Jacobian weighting by annulus. Weight different areas dark-hole for dark-hole optimization.
        dark_hole_sides:
            which side to create a dark-hole on
        
    '''
    
    mp = falco.config.ModelParameters()

    # General
    mp.lambda0 = 575e-9
    mp.Nsbp = N_subpass  # Number of sub-bandpasses to divide the whole bandpass into for estimation and control
    mp.Nwpsbp = N_waves_per_subpass # Number of wavelengths to used to approximate an image in each sub-bandpass
    mp.fracBW = fractional_bandwidth  # fractional bandwidth of the whole bandpass (Delta lambda / lambda0)
    mp.runLabel = label
    
    # Computing parameters
    mp.flagPlot = plot_outputs
    mp.flagParallel = use_parallel  # whether to use multiprocessing to parallelize some large computations
    if use_parallel: mp.Nthreads = N_threads  # Number of threads to use when using multiprocessing.
    
    # Record Keeping
    mp.TrialNum = 1
    mp.SeriesNum = 1
    mp.flagSaveWS = False
    
    # Misc
    mp.centering = 'pixel'

    # Method of computing core throughput:
    # - 'HMI' for energy within half-max isophote divided by energy at telescope pupil
    # - 'EE' for encircled energy within a radius (mp.thput_radius) divided by energy at telescope pupil
    mp.thput_metric = 'HMI'
    mp.thput_radius = 0.7  # photometric aperture radius [lambda_c/D]. Used ONLY for 'EE' method.
    mp.thput_eval_x = 7  # x location [lambda_c/D] in dark hole at which to evaluate throughput
    mp.thput_eval_y = 0  # y location [lambda_c/D] in dark hole at which to evaluate throughput

    # Where to shift the source to compute the intensity normalization value.
    mp.source_x_offset_norm = 7  # x location [lambda_c/D] in dark hole at which to compute intensity normalization
    mp.source_y_offset_norm = 0  # y location [lambda_c/D] in dark hole at which to compute intensity normalization

    # Estimation settings 
    mp.estimator = estimator # options are 'perfect' or 'pwp-bp'
    
    # Pairwise probing parameters to use if mp.estimator='pwp-bp'
    mp.est = falco.config.Object()
    mp.est.probe = falco.config.Object()
    mp.est.probe.Npairs = 3  # Number of pair-wise probe PAIRS to use.
    mp.est.probe.whichDM = 1  # Which DM # to use for probing. 1 or 2. Default is 1
    mp.est.probe.radius = 12  # Max x/y extent of probed region [actuators].
    mp.est.probe.offsetX = 0  # offset of probe center in x [actuators]. Use to avoid central obscurations.
    mp.est.probe.offsetY = 14  # offset of probe center in y [actuators]. Use to avoid central obscurations.
    mp.est.probe.axis = 'alternate'  # which axis to have the phase discontinuity along [x or y or xy/alt/alternate]
    mp.est.probe.gainFudge = 1  # empirical fudge factor to make average probe amplitude match desired value.

    # %% Wavefront Control #########################################################
    
    # %% Wavefront Control: Controller Specific
    mp.controller = 'gridsearchEFC'

    # WFSC Iterations and Control Matrix Relinearization
    mp.Nitr = N_iterations  # Number of estimation+control iterations to perform
    mp.relinItrVec = np.arange(0, mp.Nitr) # Which correction iterations at which to re-compute the control Jacobian [1-D ndarray]
    mp.dm_ind = np.array([1, 2]) # Which DMs to use [1-D ndarray]

    mp.ctrl = falco.config.Object()
    mp.ctrl.flagUseModel = True  # Whether to perform a model-based (vs empirical) grid search for the controller

    # Grid- or Line-Search Settings
    mp.ctrl.log10regVec = np.arange(-6, -2, 1/2)  # log10 of the regularization exponents (often called Beta values)
    mp.ctrl.dmfacVec = np.array([1.])  # Proportional gain term applied to DM delta command. Usually in range [0.5,1].
    
    mp.WspatialDef = spatial_weighting
    
    # Threshold for culling weak actuators from the Jacobian:
    mp.logGmin = -6  # 10^(mp.logGmin) used on the intensity of DM1 and DM2 Jacobians to weed out the weakest actuators
    
    # Zernikes to suppress with controller #########################################################
    mp.jac = falco.config.Object()
    mp.jac.zerns = np.array([1]) # Which Zernike modes to include in Jacobian. Given as the max Noll index. Always include the value "1" for the on-axis piston mode.
    mp.jac.Zcoef = 1e-9*np.ones(np.size(mp.jac.zerns))  # meters RMS of Zernike aberrations. (piston value is reset to 1 later)

    # Zernikes to compute sensitivities for #########################################################
    mp.eval = falco.config.Object()
    mp.eval.indsZnoll = np.array([])  # Noll indices of Zernikes to compute values for
    # Annuli to compute 1nm RMS Zernike sensitivities over. Columns are [inner radius, outer radius]. One row per annulus.
    mp.eval.Rsens = np.array([])  # np.array([[3., 4.], [4., 5.], [5., 8.], [8., 9.]]);  # [2-D ndarray]

    # DM parameters #########################################################
    # DM weighting
    mp.dm1.weight = 1
    mp.dm2.weight = 1
    mp.dm_ind = np.array([1, 2]) # Which DMs to use [1-D ndarray]

    # Voltage range restrictions
    mp.dm1.maxAbsV = 1000;  # Max absolute voltage (+/-) for each actuator [volts] # NOT ENFORCED YET
    mp.dm2.maxAbsV = 1000;  # Max absolute voltage (+/-) for each actuator [volts] # NOT ENFORCED YET
    mp.maxAbsdV = 1000;     # Max +/- delta voltage step for each actuator for DMs 1 and 2 [volts] # NOT ENFORCED YET

    # Deformable Mirrors Influence Functions
    mp.dm1.inf_fn = falco.INFLUENCE_XINETICS
    mp.dm2.inf_fn = falco.INFLUENCE_XINETICS
    mp.dm1.inf_sign = '+'
    mp.dm2.inf_sign = '+'

    # DM Optical Layout Parameters ###################################################
    # DM1 parameters
    mp.dm1.orientation = 'rot180'  
    mp.dm1.Nact = 48  # of actuators across DM array
    mp.dm1.dm_spacing = 0.9906e-3  # User defined actuator pitch
    mp.dm1.VtoH = 1e-9*np.ones((48, 48))  # gains of all actuators [nm/V of free stroke]
    mp.dm1.xtilt = 0  # for foreshortening. angle of rotation about x-axis [degrees]
    mp.dm1.ytilt = 9.65  # for foreshortening. angle of rotation about y-axis [degrees]
    mp.dm1.zrot = 0  # clocking of DM surface [degrees]
    mp.dm1.xc = (48/2 - 1/2)  # x-center location of DM surface [actuator widths]
    mp.dm1.yc = (48/2 - 1/2)  # y-center location of DM surface [actuator widths]
    mp.dm1.edgeBuffer = 1  

    # DM2 parameters
    mp.dm2.orientation = 'rot180'
    mp.dm2.Nact = 48  # of actuators across DM array
    mp.dm2.dm_spacing = 0.9906e-3  # User defined actuator pitch
    mp.dm2.VtoH = 1e-9*np.ones((48, 48))  # gains of all actuators [nm/V of free stroke]
    mp.dm2.xtilt = 0  # for foreshortening. angle of rotation about x-axis [degrees]
    mp.dm2.ytilt = 9.65  # for foreshortening. angle of rotation about y-axis [degrees]
    mp.dm2.zrot = 0  # clocking of DM surface [degrees]
    mp.dm2.xc = (48/2 - 1/2)  # x-center location of DM surface [actuator widths]
    mp.dm2.yc = (48/2 - 1/2)  # y-center location of DM surface [actuator widths]
    mp.dm2.edgeBuffer = 1  

    # Aperture stops at DMs
    mp.flagDM1stop = False   # Whether to apply an iris or not
    mp.dm1.Dstop = 100e-3  # Diameter of iris [meters]
    mp.flagDM2stop = True  # Whether to apply an iris or not
    mp.dm2.Dstop = 51.5596e-3  # Diameter of iris [meters]

    # DM separations
    mp.d_P2_dm1 = 0  # distance (along +z axis) from P2 pupil to DM1 [meters]
    mp.d_dm1_dm2 = 1.000  # distance between DM1 and DM2 [meters]

    # Optical Layout: All models ###################################################

    # Key Optical Layout Choices
    mp.flagSim = True  # Simulation or not
    mp.layout = 'roman_phasec_proper'  # Which optical layout to use
    mp.coro = 'HLC'
    mp.flagRotation = False  # Whether to rotate 180 degrees between conjugate planes in the compact model
    mp.flagApod = False  # Whether to use an apodizer or not
    mp.flagDMwfe = False  # Whether to use BMC DM quilting maps

    # Final Focal Plane Properties ###################################################
    mp.Fend = falco.config.Object()
    mp.Fend.res = mp.lambda0/(500e-9) * 2  # focal plane pixel sampling [ pixels per lambda0/D]
    mp.Fend.FOV = 12.0  # half-width of the field of view in both dimensions [lambda0/D]

    # Correction and scoring region definition 
    mp.Fend.corr = falco.config.Object()
    mp.Fend.corr.Rin = 2.8  # inner radius of dark hole correction region [lambda0/D]
    mp.Fend.corr.Rout = 9.7  # outer radius of dark hole correction region [lambda0/D]
    mp.Fend.corr.ang = 180  # angular opening of dark hole correction region [degrees]

    mp.Fend.score = falco.config.Object()
    mp.Fend.score.Rin = 3.0  # inner radius of dark hole scoring region [lambda0/D]
    mp.Fend.score.Rout = 9.0  # outer radius of dark hole scoring region [lambda0/D]
    mp.Fend.score.ang = 180  # angular opening of dark hole scoring region [degrees]

    mp.Fend.sides = dark_hole_sides 
    mp.Fend.clockAngDeg = 0  # Amount to rotate the dark hole location
    
    # Full Optical Layout: Full PROPER Model ###################################################
    mp.full = falco.config.Object()
    mp.full.data_dir = phasec.data_dir # Path to data needed by PROPER model
    mp.full.flagPROPER = True  # Whether the full model is a PROPER prescription

    mp.full.cor_type = 'hlc'
    mp.full.use_errors = True
    mp.full.use_lens_errors = True
    mp.full.pol_conds = pol_conditions
    mp.full.polaxis = polaxis   
    mp.full.output_dim = falco.util.ceil_even(1 + mp.Fend.res*(2*mp.Fend.FOV)) # output dim in pixels (overrides output_dim0)
    mp.full.final_sampling_lam0 = 1/mp.Fend.res # final sampling in lambda0/D
    mp.full.use_field_stop = True
    mp.full.field_stop_radius_lam0 = 9.7  # [lambda0/D]

    # Pupil Plane Resolutions
    mp.P1.full.Nbeam = 309
    mp.P1.full.Narr = 310
    
    # DM starting voltages (in the PROPER model only) ###################################################
    mp.full.dm1 = falco.config.Object()
    mp.full.dm2 = falco.config.Object()
    mp.full.dm1.flatmap = dm1_initial
    mp.full.dm2.flatmap = dm2_initial

    # Bias voltage are needed prior to WFSC to allow + and - voltages. Total voltage is mp.dm1.biasMap + mp.dm1.V
    mp.dm1.biasMap = 50 + mp.full.dm1.flatmap/mp.dm1.VtoH
    mp.dm2.biasMap = 50 + mp.full.dm2.flatmap/mp.dm2.VtoH
    
    # Optical Layout: Compact Model (and Jacobian Model) #######################################
    mp.compact = falco.config.Object()

    # Focal Lengths
    mp.fl = 1.0  # [meters] Focal length used for all FTs in compact model.

    # Pupil Plane Diameters
    mp.P2.D = 46.3e-3
    mp.P3.D = 46.3e-3
    mp.P4.D = 46.3e-3

    # Pupil Plane Resolutions
    mp.P1.compact.Nbeam = 300
    # mp.P2.compact.Nbeam = 300
    mp.P3.compact.Nbeam = 300
    mp.P4.compact.Nbeam = 300

    # Number of re-imaging relays between pupil planesin compact model. Needed to keep track of 180-degree rotations and (1/1j)^2 factors compared to the full model, which probably has extra collimated beams compared to the compact model.
    # NOTE: All these relays are ignored if mp.flagRotation == False
    mp.Nrelay1to2 = 1
    mp.Nrelay2to3 = 1
    mp.Nrelay3to4 = 1
    mp.NrelayFend = 1  # How many times to rotate the final image by 180 degrees

    # Mask Definitions ####################################################
    # Pupil definition
    mp.P1.IDnorm = 0.303  # ID of the central obscuration [diameter]. Used only for computing RMS DM surface from the ID to the OD of the pupil. OD is assumed to be 1.
    mp.P1.D = 2.3631  # telescope diameter [meters]. Used only for converting milliarcseconds to lambda0/D or vice-versa.
    mp.P1.Dfac = 1  # Factor scaling inscribed OD to circumscribed OD for the telescope pupil.
    changes = {'flagRot180': True}
    mp.P1.compact.mask = falco.mask.falco_gen_pupil_Roman_CGI_20200513(mp.P1.compact.Nbeam, mp.centering, changes)

    # Lyot stop shape
    mp.P4.IDnorm = 0.50  # Lyot stop ID [Dtelescope]
    mp.P4.ODnorm = 0.80  # Lyot stop OD [Dtelescope]
    # wStrut = 3.2/100  # Lyot stop strut width [pupil diameters]
    # rocLS = 0.02  # fillet radii [fraction of pupil diameter]
    # upsampleFactor = 100  # Lyot and FPM anti-aliasing value
    fnLS = os.path.join(mp.full.data_dir, 'hlc_20190210b', 'lyot.fits')
    LS0 = fits.getdata(fnLS)
    LS0 = falco.util.pad_crop(LS0, 311)
    LS1 = falco.mask.rotate_shift_downsample_pupil_mask(
        LS0, 309, mp.P4.compact.Nbeam, 0, 0, 0)
    mp.P4.compact.mask = falco.util.pad_crop(LS1, falco.util.ceil_even(np.max(LS1.shape)))

    # Pinhole used during back-end calibration
    mp.F3.pinhole_diam_m = 0.5*32.22*575e-9

    # Load the HLC FPM
    if mp.Nsbp == 1:
        lambdaFacs = np.array([1,])
    elif mp.Nwpsbp == 1:
        lambdaFacs = np.linspace(1-mp.fracBW/2, 1+mp.fracBW/2, mp.Nsbp)
    else:
        DeltaBW = mp.fracBW/(mp.Nsbp)*(mp.Nsbp-1)/2;
        lambdaFacs = np.linspace(1-DeltaBW, 1+DeltaBW, mp.Nsbp)

    lamUmVec = 1e6*lambdaFacs*mp.lambda0
    mp.F3.compact.Nxi = 42  # Crop down to minimum size of the spot
    mp.F3.compact.Neta = mp.F3.compact.Nxi
    mp.compact.fpmCube = np.zeros((mp.F3.compact.Nxi, mp.F3.compact.Nxi, mp.Nsbp), dtype=complex)
    for si in range(mp.Nsbp):
        lambda_um = 1e6*mp.lambda0*lambdaFacs[si]
        fn_p_r = os.path.join(mp.full.data_dir, ('hlc_20190210b/hlc_jacobian_fpm_trans_%.8fum_real.fits' % lamUmVec[si]))
        fn_p_i = os.path.join(mp.full.data_dir, ('hlc_20190210b/hlc_jacobian_fpm_trans_%.8fum_imag.fits' % lamUmVec[si]))
        fpm = fits.getdata(fn_p_r) + 1j*fits.getdata(fn_p_i)
        mp.compact.fpmCube[:, :, si] = falco.util.pad_crop(fpm, mp.F3.compact.Nxi)

    mp.F3.compact.res = 2048/309  # sampling of FPM for compact model [pixels per lambda0/D]. DO NOT CHANGE--tied to files.
    
    return mp
        

def perform_phase_retrieval(mp, quiet=False):
    # Perform an idealized phase retrieval (get the E-field directly) ************************
    optval = copy.copy(mp.full)
    optval.source_x_offset = 0
    optval.use_dm1 = True
    optval.use_dm2 = True
    nout = 1024
    optval.output_dim = 1024
    optval.use_fpm = False
    optval.use_pupil_mask = False  # No SPM for getting initial phase
    optval.use_lyot_stop = False
    optval.use_field_stop = False
    optval.use_pupil_lens = True
    delattr(optval, 'final_sampling_lam0')
    
    # Use non-SPC flat maps for SPC since SPM has separate aberrations downstream that can't be fully captured at entrance pupil with the SPM in place. The SPM aberrations are flattened in a separate step not included here.
    if 'sp' in mp.coro.lower():
        optval.dm1_m = mp.full.dm1.flatmapNoSPM
        optval.dm2_m = mp.full.dm2.flatmapNoSPM
    else:
        optval.dm1_m = mp.full.dm1.flatmap
        optval.dm2_m = mp.full.dm2.flatmap

    if mp.Nsbp == 1: lambdaFacs = np.array([1.])
    else: lambdaFacs = np.linspace(1-mp.fracBW/2, 1+mp.fracBW/2, mp.Nsbp)

    # Get the Input Pupil's E-field
    nCompact = falco.util.ceil_even(mp.P1.compact.Nbeam + 1)
    mp.P1.compact.E = np.ones((nCompact, nCompact, mp.Nsbp), dtype=complex)
    for iSubband in range(mp.Nsbp):
        print('Performing retrieval for sub-bandpass {:d}.\n'.format(iSubband+1))
        lambda_um = 1e6*mp.lambda0*lambdaFacs[iSubband]

        print('Getting aberrations from full optical train.')
        optval.pinhole_diam_m = 0  # 0 means don't use the pinhole at FPAM
        fieldFullAll, sampling = proper.prop_run('roman_phasec', lambda_um, nout, 
                                                 QUIET=quiet, PASSVALUE=optval.__dict__)
        print()
        print('Using pinhole at FPM to get back-end aberrations.')
        optval.pinhole_diam_m = mp.F3.pinhole_diam_m;
        fieldFullBackEnd, sampling = proper.prop_run('roman_phasec', lambda_um, nout, 
                                                     QUIET=quiet, PASSVALUE=optval.__dict__)
        print()
        optval.pinhole_diam_m = 0  # 0 means don't use the pinhole at FPM

        # Subtract off back-end phase aberrations from the phase retrieval estimate
        phFrontEnd = np.angle(fieldFullAll) - np.angle(fieldFullBackEnd)

        # Put front-end E-field into compact model
        fieldFull = np.abs(fieldFullAll) * np.exp(1j*phFrontEnd)
        fieldCompactReal = falco.mask.rotate_shift_downsample_pupil_mask(np.real(fieldFull), 
                                                                         mp.P1.full.Nbeam, 
                                                                         mp.P1.compact.Nbeam, 
                                                                         0, 0, 0)
        fieldCompactImag = falco.mask.rotate_shift_downsample_pupil_mask(np.imag(fieldFull), 
                                                                         mp.P1.full.Nbeam, 
                                                                         mp.P1.compact.Nbeam, 
                                                                         0, 0, 0)
        fieldCompact = fieldCompactReal + 1j*fieldCompactImag
        fieldCompact = falco.util.pad_crop(fieldCompact, (nCompact, nCompact))
        mp.P1.compact.E[:, :, iSubband] = falco.prop.relay(fieldCompact, 1, centering=mp.centering)

        if mp.flagPlot:
            plt.figure(11); plt.imshow(np.angle(fieldCompact)); plt.colorbar(); plt.hsv(); plt.pause(1e-2)
            plt.figure(12); plt.imshow(np.abs(fieldCompact)); plt.colorbar(); plt.magma(); plt.pause(0.5)

    # Don't double count the pupil amplitude with the phase retrieval and a model-based mask
    mp.P1.compact.mask = np.ones_like(mp.P1.compact.mask)
    
    print('Phase retrieval complete.')
