#!/usr/bin/env python

"""Script that solves that solves the 2D shallow water equations using finite
differences where the momentum equations are taken to be linear, but the
continuity equation is solved in its nonlinear form. The model supports turning
on/off various terms, but in its mst complete form, the model solves the following
set of eqations:

    du/dt - fv = -g*d(eta)/dx + tau_x/(rho_0*H)- kappa*u
    dv/dt + fu = -g*d(eta)/dy + tau_y/(rho_0*H)- kappa*v
    d(eta)/dt + d((eta + H)*u)/dx + d((eta + H)*u)/dy = sigma - w

where f = f_0 + beta*y can be the full latitude varying coriolis parameter.
For the momentum equations, an ordinary forward-in-time centered-in-space
scheme is used. However, the coriolis terms is not so trivial, and thus, one
first finds a predictor for u, v and then a corrected value is computed in
order to include the coriolis terms. In the continuity equation, it's used a
forward difference for the time derivative and an upwind scheme for the non-
linear terms. The model is stable under the CFL condition of

    dt <= min(dx, dy)/sqrt(g*H)    and    alpha << 1 (if coriolis is used)

where dx, dy is the grid spacing in the x- and y-direction respectively, g is
the acceleration of gravity and H is the resting depth of the fluid."""

import time
import numpy as np
import numpy.matlib
import f90nml
import argparse
import os
import shutil
import datetime

print("WELCOME to model.py, as surrogate atmospheric model for regression testing")
print("Date and time:", datetime.datetime.now())

parser = argparse.ArgumentParser(description='Surrogate model.')
parser.add_argument('--model', dest='model', action='store', type=str, default='none', help='which model to emulate (default: none)')
args = parser.parse_args()

d = {}
if args.model == 'none':
    print('Model: plain model')
    pass
elif args.model == 'cosmo':
    print('Model: COSMO model')
    d['input_nml'] = 'INPUT_ORG'
    d['pert_nl_group'] = 'runctl'
    d['pert_type'] = 'itype_pert'
    d['pert_ampl'] = 'rperturb'
    d['stat_filename'] = 'YUPRTEST'
    d['iostat_filename'] = 'YUCHKDAT'
    d['success_message'] = 'CLEAN UP'
    d['stat_onoff_filename'] = 'INPUT_DIA'
    d['stat_onoff_flag'] = 'ltestsuite'
    d['nt_filename'] = 'INPUT_ORG'
    d['nt_nl_group'] = 'runctl'
    d['nt_start_hours'] = 'hstart'
    d['nt_start_timesteps'] = 'nstart'
    d['nt_end_hours'] = 'hstop'
    d['nt_end_timesteps'] = 'nstop'
    d['aux_files'] = ['aux_dummy']
    d['input_dirname'] = 'input'
    d['input_files'] = ['in_dummy']
    d['output_dirname'] = 'output'
    d['restart_dirname'] = 'output'
elif args.model == 'fv3':
    print('Model: FV3 model')
    d['input_nml'] = 'input.nml'
    d['pert_nl_group'] = 'fv_core_nml'
    d['pert_type'] = 'perturbation_type'
    d['pert_ampl'] = 'perturbation_amplitude'
    d['stat_filename'] = 'YUPRTEST'
    d['iostat_filename'] = 'YUCHKDAT'
    d['success_message'] = 'Termination '
    d['stat_onoff_filename'] = 'input.nml'
    d['stat_onoff_flag'] = 'fv_testsuite_output'
    d['nt_filename'] = 'input.nml'
    d['nt_nl_group'] = 'coupler_nml'
    d['nt_hours'] = 'hours'
    d['nt_timesteps'] = ''
    d['aux_files'] = ['aux_dummy']
    d['input_dirname'] = 'INPUT'
    d['input_files'] = ['in_dummy']
    d['output_dirname'] = 'OUTPUT'
    d['restart_dirname'] = 'RESTART'
    with open('final_status.txt','w') as status_file:
        status_file.write(success_message + '\n')
elif args.model == 'icon':
    print('Model: ICON model')
    d['input_nml'] = 'INPUT_ORG'
    d['stat_filename'] = 'YUPRTEST'
    d['iostat_filename'] = 'YUCHKDAT'
    d['success_message'] = '0'
    d['output_dirname'] = 'output'
    d['restart_dirname'] = 'output'
else:
    print('ERROR: unknown model specified')
    exit(1)

# ==================================================================================
# ================================ Parameter stuff =================================
# ==================================================================================
# --------------- Physical prameters ---------------
L_x = 0.5E+6            # Length of domain in x-direction
L_y = 0.5E+6            # Length of domain in y-direction
g = 9.81                # Acceleration of gravity [m/s^2]
H = 100                 # Depth of fluid [m]
f_0 = 1E-4              # Fixed part ofcoriolis parameter [1/s]
beta = 2E-11            # gradient of coriolis parameter [1/ms]
rho_0 = 1024.0          # Density of fluid [kg/m^3)]
tau_0 = 0.1             # Amplitude of wind stress [kg/ms^2]
use_nonlinear = True    # True if you want non-linear advection term
use_coriolis = True     # True if you want coriolis force
use_friction = False    # True if you want bottom friction
use_wind = False        # True if you want wind stress
use_source = False      # True if you want mass source into the domain
use_sink = False        # True if you want mass sink out of the domain
param_string = "\n================================================================"
param_string += "\nuse_coriolis = {}".format(use_coriolis)
param_string += "\nuse_friction = {}\nuse_wind = {}".format(use_friction, use_wind)
param_string += "\nuse_source = {}\nuse_sink = {}".format(use_source, use_sink)
param_string += "\ng = {:g}\nH = {:g}".format(g, H)
output_freq = 30
restart_freq = 60

# --------------- Computational prameters ---------------
N_x = 50                             # Number of grid points in x-direction
N_y = 50                             # Number of grid points in y-direction
dx = L_x/(N_x - 1)                   # Grid spacing in x-direction
dy = L_y/(N_y - 1)                   # Grid spacing in y-direction
dt = 0.1*min(dx, dy)/np.sqrt(g*H)    # Time step (defined from the CFL condition)
time_step = 0                        # For counting time loop steps
start_time_step = 0                  # Start time step (for restart runs)
end_time_step = 100                  # Total number of time steps in simulation
if 'nt_filename' in d:
    nml = f90nml.read(d['input_nml'])
    if d['nt_end_hours'] in nml[d['nt_nl_group']]:
        end_time_step = nml[d['nt_nl_group']][d['nt_end_hours']] * 60
    if d['nt_end_timesteps'] in nml[d['nt_nl_group']]:
        end_time_step = nml[d['nt_nl_group']][d['nt_end_timesteps']]
    if d['nt_start_hours'] in nml[d['nt_nl_group']]:
        start_time_step = nml[d['nt_nl_group']][d['nt_start_hours']] * 60
    if d['nt_start_timesteps'] in nml[d['nt_nl_group']]:
        start_time_step = nml[d['nt_nl_group']][d['nt_start_timesteps']]
x = np.linspace(-L_x/2, L_x/2, N_x)  # Array with x-points
y = np.linspace(-L_y/2, L_y/2, N_y)  # Array with y-points
X, Y = np.meshgrid(x, y)             # Meshgrid for plotting
X = np.transpose(X)                  # To get plots right
Y = np.transpose(Y)                  # To get plots right
param_string += "\ndx = {:.2f} km\ndy = {:.2f} km\ndt = {:.2f} s".format(dx, dy, dt)

# --------------- Namelist prameters ---------------
perturbation_type = 0
perturbation_amplitude = 10.0**(-15)
if 'input_nml' in d:
    nml = f90nml.read(d['input_nml'])
    if 'pert_type' in d:
        if d['pert_type'] in nml[d['pert_nl_group']]:
            perturbation_type = nml[d['pert_nl_group']][d['pert_type']]
    if 'pert_ampl' in d:
        if d['pert_ampl'] in nml[d['pert_nl_group']]:
            perturbation_amplitude = nml[d['pert_nl_group']][d['pert_ampl']]
    if 'extra_option' in nml[d['pert_nl_group']]:
        print('\n\n>>> Extra namelist option activated <<<\n\n')

# Define friction array if friction is enabled.
if (use_friction is True):
    kappa_0 = 1/(5*24*3600)
    kappa = np.ones((N_x, N_y))*kappa_0
    param_string += "\nkappa = {:g}\nkappa/beta = {:g} km".format(kappa_0, kappa_0/(beta*1000))

# Define wind stress arrays if wind is enabled.
if (use_wind is True):
    tau_x = -tau_0*np.cos(np.pi*y/L_y)*0
    tau_y = np.zeros((1, len(x)))
    param_string += "\ntau_0 = {:g}\nrho_0 = {:g} km".format(tau_0, rho_0)

# Define coriolis array if coriolis is enabled.
if (use_coriolis is True):
    f = f_0*np.ones(len(y)) # Constant coriolis parameter

    alpha = dt*f                # Parameter needed for coriolis scheme
    beta_c = alpha**2/4         # Parameter needed for coriolis scheme

    param_string += "\nf_0 = {:g}".format(f_0)
    param_string += "\nMax alpha = {:g}".format(alpha.max())
    param_string += "\n================================================================\n"

# Define source array if source is enabled.
if (use_source):
    sigma = np.zeros((N_x, N_y))
    sigma = 0.00001*np.exp(-((X-L_x/2)**2/(2*(1E+5)**2) + (Y-L_y/2)**2/(2*(1E+5)**2)))
    
# Define source array if source is enabled.
if (use_sink is True):
    w = np.ones((N_x, N_y))*sigma.sum()/(N_x*N_y*2)

print(param_string)     # Also print parameters to screen

def yuspecif():
    with open('YUSPECIF', 'w') as yuspecif_file:
        yuspecif_file.write('''
0     The NAMELIST variables were specified as follows:
      =================================================
  
  
0     NAMELIST:  runctl
      -----------------
  
      Variable                  Actual Value      Default Value      Format
''')
        if 'input_nml' in d:
            nml = f90nml.read(d['input_nml'])
            for nl_param in ['nprocx', 'nprocy', 'nprocio']:
                yuspecif_file.write('       ' + format(nl_param,'<25') + format(nml['runctl'][nl_param],'>12d') + '       ' + format(0,'>12d') + '       ' + ' I ' + '\n')
if args.model == 'cosmo':
    yuspecif()

# ============================= Check that all inputs are here =====================

if 'aux_files' in d:
    for aux_filename in d['aux_files']:
        assert(os.path.isfile(aux_filename))
        with open(aux_filename) as aux_file:
            content = aux_file.read()
            assert(content == 'This is a dummy aux file.\n')

if 'input_dirname' in d:
    assert(os.path.isdir(d['input_dirname']))

if 'input_files' in d:
    for input_filename in d['input_files']:
        input_filename = os.path.join(d['input_dirname'], input_filename)
        assert(os.path.isfile(input_filename))
        with open(input_filename) as input_file:
            content = input_file.read()
            assert(content == 'This is a dummy input file.\n')

# ============================= Parameter stuff done ===============================

# ==================================================================================
# ==================== Allocating arrays and initial conditions ====================
# ==================================================================================
u_n = np.zeros((N_x, N_y))      # To hold u at current time step
u_np1 = np.zeros((N_x, N_y))    # To hold u at next time step
v_n = np.zeros((N_x, N_y))      # To hold v at current time step
v_np1 = np.zeros((N_x, N_y))    # To hold v at enxt time step
eta_n = np.zeros((N_x, N_y))    # To hold eta at current time step
eta_np1 = np.zeros((N_x, N_y))  # To hold eta at next time step

# Temporary variables (each time step) for upwind scheme in eta equation
h_e = np.zeros((N_x, N_y))
h_w = np.zeros((N_x, N_y))
h_n = np.zeros((N_x, N_y))
h_s = np.zeros((N_x, N_y))
uhwe = np.zeros((N_x, N_y))
vhns = np.zeros((N_x, N_y))

# Initial conditions for u and v.
u_n[:, :] = 0.0             # Initial condition for u
v_n[:, :] = 0.0             # Initial condition for u
u_n[-1, :] = 0.0            # Ensuring initial u satisfy BC
v_n[:, -1] = 0.0            # Ensuring initial v satisfy BC

# Initial condition for eta.
eta_n = np.exp(-((X-L_x/2.7)**2/(2*(0.05E+6)**2) + (Y-L_y/4)**2/(2*(0.05E+6)**2)))

# =============== Done with setting up arrays and initial conditions ===============

STAT_WRITE_HEADER = True
IOSTAT_WRITE_HEADER = True

def write_stat_file(nt, u, v, eta):
    global STAT_WRITE_HEADER
    if not 'stat_filename' in d:
        return
    if STAT_WRITE_HEADER:
        STAT_WRITE_HEADER = False
        with open(d['stat_filename'], "w+") as stat_file:
            stat_file.write(
'''#    Experiment:    Model
#    ie_tot =   49   je_tot =   49   ke =   63
#
#    var    nt  lev                         min imin jmin                         max imax jmax                        mean
''')
    if ((nt in [0,1,2,3,4,5,6,7,8,9]) or (nt % 10 == 0)):
        with open(d['stat_filename'], "a") as stat_file:
            print_stat_line(stat_file, 'u', u, nt)
            print_stat_line(stat_file, 'v', v, nt)
            print_stat_line(stat_file, 'eta', eta, nt)

def print_stat_line(file, name, field, nt):
    file.write(
        format(name,'>8') +
        format(nt,'>6d') +
        format(1,'>5d') +
        format(np.min(field), '>28.18E') +
        format(0, '>5d') +
        format(0, '>5d') +
        format(np.max(field), '>28.18E') +
        format(0, '>5d') +
        format(0, '>5d') +
        format(np.mean(field), '>28.18E') + '\n'
    )

def perturb(nt, u, v, eta):
    global perturbation_type
    global perturbation_amplitude
    if perturbation_type == 0:
        return
    if ((perturbation_type == 1) and (nt > 0)):
        return
    if perturbation_amplitude >= 0.0:
        ampl = perturbation_amplitude
    else:
        ampl = -perturbation_amplitude * (10.0**(-15))
    field_perturb('u', u, ampl)
    field_perturb('v', v, ampl)
    field_perturb('eta', eta, ampl)

def field_perturb(name, field, ampl):
    print('>>> perturbing %s with amplitude %E' % (name, ampl))
    r = np.random.uniform(size=np.shape(field))
    r = ampl * (2.0 * r - 1.0)
    field *= (1.0 + r)

def print_iostat_line(file, ee, name, field, nt):
    file.write(
        '  ' +
        format(name,'<10') +
        format(ee, '>4d') +
        format(1,'>4d') +
        format(np.min(field), '>15.6f') +
        format(0, '>5d') +
        format(0, '>5d') +
        '   ' +
        format(np.max(field), '>18.6f') +
        format(0, '>5d') +
        format(0, '>5d') +
        '   ' +
        format(np.mean(field), '>18.6f') + '\n'
    )

def write_iostat_file(nt, ee, field, fieldname, filename):
    global IOSTAT_WRITE_HEADER
    if not 'iostat_filename' in d:
        return
    if IOSTAT_WRITE_HEADER:
        IOSTAT_WRITE_HEADER = False
        with open(d['iostat_filename'], "w+") as iostat_file:
            iostat_file.write('''
Check the file data: 
    File:   %s
    ie_tot =   70   je_tot =    7   ke_tot =   80
    
     var       ee    lev         min      imin   jmin          max      imax   jmax         mean  
''' % filename)
    with open(d['iostat_filename'], "a") as iostat_file:
        print_iostat_line(iostat_file, ee, fieldname, field, nt)

def write_output(nt, u, v, eta):
    global IOSTAT_WRITE_HEADER
    IOSTAT_WRITE_HEADER = True
    output_filename = 'lfff' + format(time_step, '>08d')
    if 'output_dirname' in d:
        output_filename = os.path.join(d['output_dirname'], output_filename)
    with open(output_filename,'wb') as output_file:
        output_file.write(bytes('GRIB','utf-8'))
        np.save(output_file,u)
        write_iostat_file(nt, 13, u, 'u', output_filename)
        np.save(output_file,v)
        write_iostat_file(nt, 17, v, 'v', output_filename)
        np.save(output_file,eta)
        write_iostat_file(nt, 33, eta, 'eta', output_filename)
        np.save(output_file,u*u+v*v)
        write_iostat_file(nt, 102, u*u+v*v, 'KE', output_filename)
    shutil.copyfile(output_filename, output_filename+'.nc')

def write_restart(nt, u, v, eta):
    restart_filename = 'lrff' + format(time_step, '>08d')
    if 'restart_dirname' in d:
        restart_filename = os.path.join(d['restart_dirname'], restart_filename)
    with open(restart_filename,'wb') as restart_file:
        restart_file.write(bytes('GRIB','utf-8'))
        np.save(restart_file,u)
        np.save(restart_file,v)
        np.save(restart_file,eta)

# ==================================================================================
# ========================= Main time loop for simulation ==========================
# ==================================================================================

while (time_step <= end_time_step):

    if time_step >= start_time_step:
        print("Timestep = ", time_step)
        if time_step % output_freq == 0:
            write_output(time_step, u_n, v_n, eta_n)
        if time_step % restart_freq == 0:
            write_restart(time_step, u_n, v_n, eta_n)
        write_stat_file(time_step, u_n, v_n, eta_n)

    perturb(time_step, u_n, v_n, eta_n)

    # ------------ Computing values for u and v at next time step --------------
    u_np1[:-1, :] = u_n[:-1, :] - g*dt/dx*(eta_n[1:, :] - eta_n[:-1, :])
    v_np1[:, :-1] = v_n[:, :-1] - g*dt/dy*(eta_n[:, 1:] - eta_n[:, :-1])

    # Non-linear advection if enabled
    if (use_nonlinear is True):
        u_np1[1:-1, :] -= dt/dx/2.0 * u_n[1:-1, :] * ( u_n[2:, :] - u_n[:-2, :] )
        v_np1[:, 1:-1] -= dt/dy/2.0 * v_n[:, 1:-1] * ( v_n[:, 2:] - v_n[:, :-2] )

    # Add friction if enabled.
    if (use_friction is True):
        u_np1[:-1, :] -= dt*kappa[:-1, :]*u_n[:-1, :]
        v_np1[:-1, :] -= dt*kappa[:-1, :]*v_n[:-1, :]

    # Add wind stress if enabled.
    if (use_wind is True):
        u_np1[:-1, :] += dt*tau_x[:]/(rho_0*H)
        v_np1[:-1, :] += dt*tau_y[:]/(rho_0*H)

    # Use a corrector method to add coriolis if it's enabled.
    if (use_coriolis is True):
        u_np1[:, :] = (u_np1[:, :] - beta_c*u_n[:, :] + alpha*v_n[:, :])/(1 + beta_c)
        v_np1[:, :] = (v_np1[:, :] - beta_c*v_n[:, :] - alpha*u_n[:, :])/(1 + beta_c)

    v_np1[:, -1] = 0.0      # Northern boundary condition
    u_np1[-1, :] = 0.0      # Eastern boundary condition
    # -------------------------- Done with u and v -----------------------------

    # --- Computing arrays needed for the upwind scheme in the eta equation.----
    h_e[:-1, :] = np.where(u_np1[:-1, :] > 0, eta_n[:-1, :] + H, eta_n[1:, :] + H)
    h_e[-1, :] = eta_n[-1, :] + H

    h_w[0, :] = eta_n[0, :] + H
    h_w[1:, :] = np.where(u_np1[:-1, :] > 0, eta_n[:-1, :] + H, eta_n[1:, :] + H)

    h_n[:, :-1] = np.where(v_np1[:, :-1] > 0, eta_n[:, :-1] + H, eta_n[:, 1:] + H)
    h_n[:, -1] = eta_n[:, -1] + H

    h_s[:, 0] = eta_n[:, 0] + H
    h_s[:, 1:] = np.where(v_np1[:, :-1] > 0, eta_n[:, :-1] + H, eta_n[:, 1:] + H)

    uhwe[0, :] = u_np1[0, :]*h_e[0, :]
    uhwe[1:, :] = u_np1[1:, :]*h_e[1:, :] - u_np1[:-1, :]*h_w[1:, :]

    vhns[:, 0] = v_np1[:, 0]*h_n[:, 0]
    vhns[:, 1:] = v_np1[:, 1:]*h_n[:, 1:] - v_np1[:, :-1]*h_s[:, 1:]
    # ------------------------- Upwind computations done -------------------------

    # ----------------- Computing eta values at next time step -------------------
    eta_np1[:, :] = eta_n[:, :] - dt*(uhwe[:, :]/dx + vhns[:, :]/dy)    # Without source/sink

    # Add source term if enabled.
    if (use_source is True):
        eta_np1[:, :] += dt*sigma

    # Add sink term if enabled.
    if (use_sink is True):
        eta_np1[:, :] -= dt*w
    # ----------------------------- Done with eta --------------------------------

    u_n = np.copy(u_np1)        # Update u for next iteration
    v_n = np.copy(v_np1)        # Update v for next iteration
    eta_n = np.copy(eta_np1)    # Update eta for next iteration

    time_step += 1

# ============================= Main time loop done ================================

print("Main computation loop done!")

if 'success_message' in d:
    print(d['success_message'])
