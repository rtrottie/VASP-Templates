#!/usr/bin/env python
import os
import shutil
from custodian.vasp.jobs import *
from custodian.vasp.handlers import *
from custodian.custodian import *
from Classes_Custodian import *
from Classes_Pymatgen import *

shutil.copy('../../INCAR', 'INCAR')
shutil.copy('../../KPOINTS', 'KPOINTS')
shutil.copy('../../POTCAR', 'POTCAR')
try:
        shutil.copy('POSCAR.real', 'POSCAR')
except:
        pass

incar = Incar.from_file('INCAR')
handlers = []
if 'AUTO_GAMMA' in incar and incar['AUTO_GAMMA']:
    vasp = os.environ['VASP_GAMMA']
else:
    vasp = os.environ['VASP_KPTS']
if 'AUTO_NUPDOWN' in incar:



vaspjob = [StandardJob([os.environ['VASP_MPI'], '-np', os.environ['VASP_PROCS'], vasp], 'vasp.log', auto_npar=False, backup=False)]
c = Custodian(handlers, vaspjob, max_errors=10)
c.run()