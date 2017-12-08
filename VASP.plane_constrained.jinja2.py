{% extends "VASP.base.jinja2.sh" %}

{% block environment %}
source ~/.bashrc_vasp
export OMP_NUM_THREADS={{ openmp }}
export VASP_PROCS={{ tasks }}
{% endblock environment %}

{% block python %}
from Classes_ASE import StandardVasp as Vasp
from Classes_ASE import converged_fmax_or_emax
from Classes_Pymatgen import Incar
from ase.io import read
from ase.optimize.precon.fire import PreconFIRE as Optimizer
import logging
import sys

FORMAT = '%(asctime)s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.INFO, filename='run.log')
root = logging.getLogger()
root.setLevel(logging.DEBUG)
ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

i = Incar.from_file('INCAR')
atoms = read('POSCAR')
if 'CONSATOM3' in i and 'CONTINUE_3PT' in i:
    from Classes_ASE import LockedTo3AtomPlane
    print('3 Atom Constraint cont.')
    c = LockedTo3AtomPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']))
if 'CONSATOM3' in i:
    from Classes_ASE import InPlane as KeepInPlane
    print('3 Atom Constraint')
    c = KeepInPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']))
elif 'SURFACE_REFERENCE' in i:
    from Classes_ASE import InMPPlane_SurfaceReference as KeepInPlane
    print('Perpendicular Constraint using Reference POSCAR')
    c=KeepInPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2']), i['SURFACE_REFERENCE'])
else:
    from Classes_ASE import InMPPlaneXY as KeepInPlane
    print('Perpendicular Constraint')
    c = KeepInPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2']))



atoms.set_calculator(Vasp())
i = Incar.from_file('INCAR')
i['NSW'] = 0
i['IBRION'] = -1
if 'IOPT' in i:
    del i['IOPT']
i.write_file('INCAR')
atoms.set_constraint(c)

Optimizer.converged = converged_fmax_or_emax
dyn = Optimizer(atoms, trajectory='run.traj', restart='history.pckl')
dyn.run(fmax=i['EDIFFG'])
print('Done')

{% endblock python %}
