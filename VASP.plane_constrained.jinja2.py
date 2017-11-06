{% extends "VASP.base.jinja2.sh" %}

{% block environment %}
source ~/.bashrc_vasp
export OMP_NUM_THREADS={{ openmp }}
export VASP_PROCS={{ tasks }}
{% endblock environment %}

{% block python %}
from Classes_ASE import StandardVasp as Vasp
from Classes_ASE import converged_fmax_as_emax
from Classes_Pymatgen import Incar
from ase.io import read
from ase.optimize.precon import PreconFIRE as Optimizer

i = Incar.from_file('INCAR')
if 'CONSATOM3' in i:
    from Classes_ASE import InPlane as KeepInPlane
    c = KeepInPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']))
else:
    from Classes_ASE import InMPPlane as KeepInPlane
    c = KeepInPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2']))



atoms = read('POSCAR')
atoms.set_calculator(Vasp())
i = Incar.from_file('INCAR')
i['NSW'] = 0
i['IBRION'] = -1
if 'IOPT' in i:
    del i['IOPT']
i.write_file('INCAR')
atoms.set_constraint(c)

Optimizer.converged = converged_fmax_as_emax
dyn = Optimizer(atoms, trajectory='run.traj', restart='history.pckl')
dyn.run(fmax=i['EDIFFG'])
print('Done')

{% endblock python %}
