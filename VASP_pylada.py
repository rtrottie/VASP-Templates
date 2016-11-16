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

    # Determine wheter to use Gamma optimized vasp
    incar = Incar.from_file('INCAR')
    if 'AUTO_GAMMA' in incar and incar['AUTO_GAMMA']:
        vasp = os.environ['VASP_GAMMA']
    else:
        vasp = os.environ['VASP_KPTS']

    handlers = [WalltimeHandler()]
    vaspjob = [StandardJob(['mpirun', '-np', os.environ['VASP_PROCS'], vasp], 'vasp.log', auto_npar=False, backup=False,
                           settings_override=override, suffix=suffix, final=False)]
    c = Custodian(handlers, vaspjob, max_errors=10)
    c.run()

def fix_incar(incar: Incar):
    fix_bad_good = [ ( 'LDUU', 'LDAUU' ),
                     ( 'LDUL', 'LDAUL' ),
                     ( 'LDUJ', 'LDAUJ' )]
    for bad, good in fix_bad_good:
        if bad in incar:
            incar[good] = incar[bad]
            del incar[bad]
    return incar


# incar = fix_incar(Incar.from_file('INCAR'))
# incar.write_file('INCAR')
run_vasp()
exitcode = 0