{% extends "VASP.base.jinja2.sh" %}
{% block python %}
from custodian.custodian import *
from Classes_Custodian import *
import Upgrade_Run
import logging
import copy
import subprocess

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, filename='run.log')
jobtype = '{{ jobtype }}'
vasp_kpts = '{{ vasp_kpts }}'
vasp_gamma =  '{{ vasp_gamma }}'


handlers = [WalltimeHandler({{ time }}*60*60, min(30*60, {{ time }}*60*60/20), electronic_step_stop=True)]


def get_runs(max_steps=1000):
    nsteps = 20
    for i in range(max_steps):
        if i > 0:
            continuation = [{'file': os.path.join('01', 'CONTCAR'),
                             'action': {'_file_copy': {'dest': os.path.join('POSCAR')}}},
                            {'file': os.path.join('01', 'CONTCAR'),
                             'action': {'_file_copy': {'dest': os.path.join('01', 'POSCAR')}}},
                            {'file': os.path.join('01', 'OUTCAR'),
                             'action': {
                                 '_file_copy': {'dest': os.path.join('01', 'OUTCAR.{}'.format(str(i).zfill(3)))}}},
                            {'file': os.path.join('01', 'CONTCAR'),
                             'action': {
                                 '_file_copy': {'dest': os.path.join('01', 'CONTCAR.{}'.format(str(i).zfill(3)))}}},
                            ]
        else:
            continuation = []
        nsteps = nsteps + 5
        if i > 0 and ((not os.path.exists('CONTCAR') or os.path.getsize('CONTCAR') == 0) and (not os.path.exists('01/CONTCAR') or os.path.getsize('01/CONTCAR') == 0)):
            raise Exception('empty CONTCAR')
        incar = Incar.from_file('INCAR')
        try:
            nebef = subprocess.Popen('nebef.pl', stdout=subprocess.PIPE)
            force = float(nebef.stdout.readlines()[0].split()[1])
            o = Outcar('01/OUTCAR')
            o.read_neb()
            logging.info('Force :  {}\nEnergy:  {}'.format(force, o.data['energy']))
            if force < -incar['EDIFFG']:
                final = True
            else:
                final = False

        except:
            final = False
        if ('AUTO_GAMMA' in incar and incar['AUTO_GAMMA']):
            vasp = vasp_gamma
        else:
            vasp = vasp_kpts
        yield DiffusionJob(incar['DIFFATOM'], [incar['CONSATOM1'], incar['CONSATOM2'], incar['CONSATOM3']], nsteps,
                           vasp_cmd=['{{ mpi }}', '-np', '{{ tasks }}', vasp], output_file='{{ logname }}', auto_npar=False, final=final, settings_override=continuation)

c = Custodian(handlers, get_runs(), max_errors=10)
c.run()
{% endblock python %}
