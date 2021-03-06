#!/usr/bin/env python
import os
import shutil
from custodian.vasp.jobs import *
from custodian.vasp.handlers import *
import numpy as np
from custodian.custodian import *
from Classes_Pymatgen import *
from Classes_Custodian import StandardJob



def energy(suffix=''):
    """
    Gets energy for run in current directory

    :return:
    """
    from pymatgen.io.vasp.outputs import Vasprun
    v = Vasprun('vasprun.xml' + suffix, parse_dos=False, parse_eigen=False)
    return v.final_energy

def run_vasp(override=[], suffix='', walltime=None, buffer_time=None):
    """
    execute vasp with given override and suffix

    :param override:
    :param suffix:
    :return:
    """
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
    if walltime:
        handlers += [WalltimeHandler(wall_time=walltime, buffer_time=buffer_time, electronic_step_stop=True,)]

    if os.environ['VASP_MPI'] == 'srun':
        vaspjob = [StandardJob(['srun', vasp], 'vasp.log', auto_npar=False, backup=False,
                               settings_override=override, suffix=suffix, final=False)]
    else:
        vaspjob = [StandardJob(['mpirun', '-np', os.environ['VASP_PROCS'], vasp], 'vasp.log', auto_npar=False, backup=False,
                               settings_override=override, suffix=suffix, final=False)]
    c = Custodian(handlers, vaspjob, max_errors=10)
    c.run()

try:
        shutil.copy('POSCAR.real', 'POSCAR')
except:
        pass

incar = Incar.from_file('INCAR')
# Check for NUPDOWNdd
if os.path.exists('nupdown_info') and 'AUTO_NUPDOWN' in incar:  # Determine if full check must be done or if just using past NUPDOWN
    with open('nupdown_info') as f:
        lines = f.readlines()
        nupdown_best = int(lines[0].strip())  # optimal NUPDOWN is first line
        nupdown_iters = int(lines[1].strip()) # number of iterations with best nupdown
    if nupdown_iters < incar['AUTO_NUPDOWN_ITERS']:
        nupdown_check = False
    else:
        nupdown_check = True
else:
    nupdown_check = True

if 'PBS_START_TIME' in os.environ:
    import calendar
    start_time = int(os.environ['PBS_START_TIME'])
    current_time = calendar.timegm(time.gmtime())
    elapsed_time = current_time - start_time
    if 'PBS_WALLTIME' in os.environ:
        orig_walltime = int(os.environ['PBS_WALLTIME'])
    else:
        orig_walltime = 240*60*60
    walltime = orig_walltime - elapsed_time
    buffer_time = min(45 * 60, walltime / 20)
    if buffer_time*2 > walltime:
        exitcode = 101
        raise Exception('Not Enough Time')
else:
    walltime = None
    buffer_time = None


if 'AUTO_NUPDOWN' in incar and not nupdown_check: # have a guess of nupdown
    override = [{"dict": "INCAR",  "action": {"_set": {"NUPDOWN": nupdown_best}}}]
    run_vasp(override)
    with open('nupdown_info', 'w') as f:
        f.writelines([str(nupdown_best), '\n', str(nupdown_iters+1)])
elif 'AUTO_NUPDOWN' in incar and nupdown_check: # First run in new folder
        energies = []

        def is_int(s):
            try:
                int(s)
                return True
            except:
                return False
        auto_nupdown = [ int(x) for x in incar['AUTO_NUPDOWN'].split()[1:]]
        for nupdown in auto_nupdown:  # get energies for each desired NUPDOWN
            override = [{"dict": "INCAR",
                         "action": {"_set": {"NUPDOWN": nupdown,
                                             'ISTART': 0,        # Don't use previously converged WAVECAR and CHGCAR
                                             'ICHARG': 2,
                                             'NELM'  : incar['NELM']*2}}}]
            suffix = '.' + str(nupdown)
            run_vasp(override, suffix)
            energies.append(energy(suffix))
        with open('nupdown_info', 'w') as f: # store info for later use
            i = np.argmin(energies) # get index minima
            nupdown_best = auto_nupdown[i]
            f.writelines([str(nupdown_best), '\n0'])
        suffix = '.' + str(nupdown_best)
        files = [f for f in os.listdir('.') if f.endswith('.' + str(nupdown_best))]
        for f in files:
            shutil.copy(f, f[:-len('.' + str(nupdown_best))])

else:
    run_vasp(walltime=walltime, buffer_time=buffer_time)

exitcode = 0