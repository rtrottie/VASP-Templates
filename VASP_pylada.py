#!/usr/bin/env python
import os
import shutil
from custodian.vasp.jobs import *
from custodian.vasp.handlers import *
import numpy as np
from custodian.custodian import *
from Classes_Pymatgen import *
from Classes_Custodian import StandardJob, NEBJob
import shutil
import calendar
import time
from math import floor,ceil

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, filename='run.log')

class NEBJobSinglePylada(NEBJob):
    def postprocess(self):
        src = '01'
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(item)
            if os.path.isdir(s):
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
        return super().postprocess()

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
    handlers = [NonConvergingErrorHandler(nionic_steps=20, change_algo=True), PositiveEnergyErrorHandler()]
    if 'PBS_START_TIME' in os.environ:
        start_time = int(os.environ['PBS_START_TIME'])
        current_time = calendar.timegm(time.gmtime())
        elapsed_time = current_time - start_time
        walltime = int(os.environ['PBS_WALLTIME']) - elapsed_time
        logging.info('Walltime : {}'.format(walltime))
        handlers += [WalltimeHandler(wall_time=walltime, buffer_time=min(45*60, walltime*60*60/20), electronic_step_stop=True,)]
    if ('IMAGES' in incar and 'ICHAIN' in incar) and (incar['IMAGES'] == 1 and incar['ICHAIN'] == 0):
        if 'POSCAR' in os.listdir():
            inital_images =  ceil((incar['IMAGES'] - 1) / 2) + 1
            final_images  = floor((incar['IMAGES'] - 1) / 2) + 1
            initial = Poscar.from_file('00/POSCAR').structure # type: Structure
            ts = Poscar.from_file('POSCAR') # type: Structure
            final = Poscar.from_file(str(incar['IMAGES']+1).zfill(2), 'POSCAR') # type: Structure
            # TODO: Don't force interpolation
            images = initial.interpolate(ts, inital_images, autosort_tol=0.75)[:-1] # get images up to, but not including, the TS
            images += ts.interpolate(final, final_images, autosort_tol=0.75) # get images from TS
            image_i = 0
            for image in images: # type: Structure
                image_dir = os.path.join(str(image_i).zfill(2))
                os.makedirs(image_dir, exist_ok=True)
                image.to(fmt='poscar', filename=os.path.join(image_dir, 'POSCAR'))
                image_i = image_i + 1

        vaspjob = [NEBJobSinglePylada(['mpirun', '-np', os.environ['PBS_NP'], vasp], 'vasp.log', auto_npar=False, backup=False,
                           settings_override=override, suffix=suffix, final=False)]
    else:
        vaspjob = [StandardJob(['mpirun', '-np', os.environ['PBS_NP'], vasp], 'vasp.log', auto_npar=False, backup=False,
                               settings_override=override, suffix=suffix, final=False)]
    c = Custodian(handlers, vaspjob, max_errors=10)
    if 'STOPCAR' in os.listdir():
        os.remove('STOPCAR')
    c.run()

def fix_incar(incar: Incar):
    # fix_bad_good = [ ( 'LDUU', 'LDAUU' ),
    #                  ( 'LDUL', 'LDAUL' ),
    #                  ( 'LDUJ', 'LDAUJ' )]
    # for bad, good in fix_bad_good:
    #     if bad in incar:
    #         incar[good] = incar[bad]
    #         del incar[bad]
    if 'GGA' in incar and 'P' in incar['GGA'] and 's' in incar['GGA']:
        incar['GGA']='PS'

    return incar


incar = fix_incar(Incar.from_file('INCAR'))
incar.write_file('INCAR')
run_vasp()
exitcode = 0