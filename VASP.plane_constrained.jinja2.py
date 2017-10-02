{% extends "VASP.base.jinja2.sh" %}

{% block environment %}
source ~/.bashrc_vasp
export OMP_NUM_THREADS={{ openmp }}
export VASP_PROCS={{ tasks }}
{% endblock environment %}

{% block python %}
from Classes_ASE import StandardVasp as Vasp
from Classes_ASE import InvertPlane, InPlane, HookeanPlane
from Classes_Pymatgen import Incar
from ase.io import read
from ase.optimize.precon import PreconFIRE as FIRE

atoms = read('POSCAR')
atoms.set_calculator(Vasp())
i = Incar.from_file('INCAR')
i['NSW'] = 0
i['IBRION'] = -1
if 'IOPT' in i:
    del i['IOPT']
i.write_file('INCAR')
c = HookeanPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']))
atoms.set_constraint(c)

dyn = FIRE(atoms, trajectory='run.traj', restart='history.pckl')
dyn.run(fmax=i['EDIFFG']*-2)

import os
os.makedirs('improved_ts', exist_ok=True)
os.chdir('improved_ts')
atoms = read('POSCAR')
atoms.set_calculator(Vasp())
i = Incar.from_file('INCAR')
c = InvertPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']))
atoms.set_constraint(c)
dyn = FIRE(atoms)
dyn.run(fmax=i['EDIFFG']*-1)
{% endblock python %}
