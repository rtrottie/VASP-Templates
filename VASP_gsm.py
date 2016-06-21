#!/usr/bin/env python
import os
import shutil
from custodian.vasp.jobs import *
from custodian.vasp.handlers import *
import numpy as np
from custodian.custodian import *
from Classes_Pymatgen import *
from Classes_Custodian import StandardJob

def is_int(s):
    try:
        int(s)
        return True
    except:
        return False

def energy(suffix=''):
    '''
    Gets energy for run in current directory

    :return:
    '''
    from pymatgen.io.vasp.outputs import Vasprun
    v = Vasprun('vasprun.xml' + suffix, parse_dos=False, parse_eigen=False)
    return v.final_energy

def run_vasp(override=[], suffix=''):
    '''
    execute vasp with given override and suffix

    :param override:
    :param suffix:
    :return:
    '''
    from Classes_Pymatgen import Incar
    from Classes_Custodian import StandardJob
    from custodian.custodian import Custodian
    import os

    # Determine wheter to use Gamma optimized vasp
    incar = Incar.from_file('INCAR')
    if 'AUTO_GAMMA' in incar and incar['AUTO_GAMMA']:
        vasp = os.environ['VASP_GAMMA']
    else:
        vasp = os.environ['VASP_KPTS']

    handlers = []
    vaspjob = [StandardJob([vasp, '-np', os.environ['VASP_PROCS'], vasp], 'vasp.log', auto_npar=False, backup=False,
                           settings_override=override, suffix=suffix)]
    c = Custodian(handlers, vaspjob, max_errors=10)
    c.run()

shutil.copy('../../INCAR', 'INCAR')
shutil.copy('../../KPOINTS', 'KPOINTS')
shutil.copy('../../POTCAR', 'POTCAR')
try:
        shutil.copy('POSCAR.real', 'POSCAR')
except:
        pass

incar = Incar.from_file('INCAR')
# Check for NUPDOWN
if os.path.exists('nupdown_info'):  # Determine if full check must be done or if just using past NUPDOWN
    with open('nupdown_info') as f:
        lines = f.readlines()
        nupdown_best = lines[0]  # optimal NUPDOWN is first line
        nupdown_iters = lines[1] # number of iterations with best nupdown
    if nupdown_iters < incar['AUTO_NUPDOWN_ITERS']:
        nupdown_check = False
    else:
        nupdown_check = True
else:
    nupdown_check = True

if 'AUTO_NUPDOWN' in incar and not nupdown_check: # have a guess of nupdown
    override = [{"dict": "INCAR",  "action": {"_set": {"NUPDOWN": nupdown_best}}}]
    run_vasp(override)
elif 'AUTO_NUPDOWN' in incar and nupdown_check: # First run in new folder
        energies = []
        auto_nupdown = [ int(x) for x in incar['AUTO_NUPDOWN'].split() if is_int(x)]
        for nupdown in auto_nupdown:  # get energies for each desired NUPDOWN
            override = [{"dict": "INCAR",
                         "action": {"_set": {"NUPDOWN": nupdown,
                                             'ISTART': 0,        # Don't use previously converged WAVECAR and CHGCAR
                                             'ICHARG': 2}}}]
            suffix = '.' + str(nupdown)
            run_vasp(override, suffix)
            energies.append(energy(suffix))
        with open('nupdown_info', 'w') as f: # store info for later use
            i = np.argmin(energies) # get index minima
            nupdown_best = auto_nupdown[i]
            f.writelines([str([nupdown_best]), '0'])
        suffix = '.' + str(nupdown_best)
        files = [f for f in os.listdir('.') if f.endswith(suffix)]
        for f in files:
            shutil.copy(f, f[:-len(suffix)])

else:
    run_vasp()


