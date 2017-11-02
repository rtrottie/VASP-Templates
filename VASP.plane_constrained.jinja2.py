{% extends "VASP.base.jinja2.sh" %}

{% block environment %}
source ~/.bashrc_vasp
export OMP_NUM_THREADS={{ openmp }}
export VASP_PROCS={{ tasks }}
{% endblock environment %}

{% block python %}
from Classes_ASE import StandardVasp as Vasp
from Classes_ASE import InPlane as KeepInPlane
from Classes_Pymatgen import Incar
from ase.io import read
from tsase.optimize import SDLBFGS as Optimizer

atoms = read('POSCAR')
atoms.set_calculator(Vasp())
i = Incar.from_file('INCAR')
i['NSW'] = 0
i['IBRION'] = -1
if 'IOPT' in i:
    del i['IOPT']
i.write_file('INCAR')
c = KeepInPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']))
atoms.set_constraint(c)

dyn = Optimizer(atoms, trajectory='run.traj', restart='history.pckl')
dyn.run(emax=1e-6)

{% endblock python %}
