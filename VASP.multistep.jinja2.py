{% extends "VASP.base.jinja2.sh" %}
{% block python %}
from custodian.custodian import *
from Classes_Custodian import *
import Upgrade_Run
import logging
import copy

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, filename='run.log')
jobtype = '{{ jobtype }}'
vasp_kpts = '{{ vasp_kpts }}'
vasp_gamma =  '{{ vasp_gamma }}'


if jobtype == 'NEB':
    handlers = [WalltimeHandler({{ time }}*60*60, 15*60, electronic_step_stop=True), NEBNotTerminating('{{ logname }}', 180*60)]
    job = NEBJob
    images = Incar.from_file('INCAR')['IMAGES']
    continuation = []
    for i in range(1, images+1):
        folder = str(i).zfill(2)
        continuation.append({'file': os.path.join(folder, 'CONTCAR'),
                             'action': {'_file_copy': {'dest': os.path.join(folder, 'POSCAR')}}})
elif jobtype == 'Dimer':
    handlers = [WalltimeHandler({{ time }}*60*60, 15*60, electronic_step_stop=True), NEBNotTerminating('{{ logname }}', 180*60),
                DimerDivergingHandler(), UnconvergedErrorHandler()]
    job = DimerJob
    continuation = [{'file': 'CONTCAR',
                     'action': {'_file_copy': {'dest': 'POSCAR'}}},
                    {'file': 'NEWMODECAR',
                     'action' : {'_file_copy': {'dest': 'MODECAR'}}}]
elif jobtype == 'Standard':
    handlers = [WalltimeHandler({{ time }}*60*60, electronic_step_stop=True), UnconvergedErrorHandler()]
    job = StandardJob
    continuation = [{'file': 'CONTCAR',
                     'action': {'_file_copy': {'dest': 'POSCAR'}}}]


def get_runs(max_steps=100):
    for i in xrange(max_steps):
        if jobtype != 'NEB' and i > 0 and (not os.path.exists('CONTCAR') or os.path.getsize('CONTCAR') == 0):
            raise Exception('empty CONTCAR')
        incar = Incar.from_file('INCAR')
        stages = Upgrade_Run.parse_incar_update('{{ CONVERGENCE }}')
        stage_number = incar['STAGE_NUMBER']
        if i == 0:
            settings = Upgrade_Run.parse_stage_update(stages[incar['STAGE_NUMBER']], incar)
        else:
            stage_number += 1
            if stage_number >= len(stages):
                break
            settings = Upgrade_Run.parse_stage_update(stages[stage_number], incar)
            settings += continuation
        if stage_number == len(stages) - 1:
            final = True
        else:
            final = False
        if 'AUTO_GAMMA' in incar and incar['AUTO_GAMMA']:
            vasp = vasp_gamma
        else:
            vasp = vasp_kpts
        yield job(['{{ mpi }}', '-np', '{{ tasks }}', vasp], '{{ logname }}', auto_npar=False, settings_override=settings, final=final)


c = Custodian(handlers, get_runs(), max_errors=10)
c.run()
{% endblock python %}
