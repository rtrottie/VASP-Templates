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
from ase import Atoms
from ase.optimize.precon.fire import PreconFIRE as Optimizer
import numpy as np
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

iterate = None
i = Incar.from_file('INCAR')
atoms = read('POSCAR')# type: Atoms
if 'CONSATOM3' in i and 'CONTINUE_3PT' in i:
    from Classes_ASE import LockedTo3AtomPlane
    print('3 Atom Constraint cont.')
    a = read('POSCAR')# type: Atoms
    c = LockedTo3AtomPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']), a.positions[i['DIFFATOM']])
if 'CONSTYPE' in i and i['CONSTYPE'] == 'Bond':
    if 'ITERATE' in i and i['ITERATE']:
        from ase.constraints import FixInternals
        print('Constraining Bonds to fixed length')
        bond1 = atoms.get_distance(i['DIFFATOM'], i['CONSATOM1'], mic=True)
        bond2 = atoms.get_distance(i['DIFFATOM'], i['CONSATOM2'], mic=True)
        bonds = [
            [ bond1, [ i['DIFFATOM'], i['CONSATOM1'] ] ],
            [ bond2, [ i['DIFFATOM'], i['CONSATOM2'] ] ]
                ]
        c = FixInternals(bonds=bonds)
        def iterate(atoms : Atoms):
            delta = 0.01
            global bond1
            global bond2
            force = atoms.get_forces()[i['DIFFATOM']]
            bond1_dist   = atoms.get_distance(i['DIFFATOM'], i['CONSATOM1'], vector=False)
            bond1_vector = atoms.get_distance(i['DIFFATOM'], i['CONSATOM1'], vector=True )
            bond1_unit = bond1_vector / bond1_dist
            bond2_dist   = atoms.get_distance(i['DIFFATOM'], i['CONSATOM2'], vector=False)
            bond2_vector = atoms.get_distance(i['DIFFATOM'], i['CONSATOM2'], vector=True )
            bond2_unit = bond2_vector / bond2_dist

            bond1_projection = np.dot(force, bond1_unit)
            bond2_projection = np.dot(force, bond2_unit)
            if abs(bond1_projection) > bond2_projection:
                if bond1_projection > 0:
                    print('Growing Bond 1')
                    bond1 += delta
                    bond2 -= delta / 4
                else:
                    print('Shrinking Bond 1')
                    bond1 -= delta
                    bond2 += delta / 4
            else:
                if bond2_projection > 0:
                    print('Growing Bond 2')
                    bond2 += delta
                    bond1 -= delta / 4
                else:
                    print('Shrinking Bond 2')
                    bond2 -= delta
                    bond1 += delta / 4
            bonds = [
                [ bond1, [ i['DIFFATOM'], i['CONSATOM1'] ] ],
                [ bond2, [ i['DIFFATOM'], i['CONSATOM2'] ] ]
                    ]
            return FixInternals(bonds=bonds)

    else:
        from ase.constraints import FixBondLengths
        print('Constraining Bonds')
        c = FixBondLengths([[i['DIFFATOM'], i['CONSATOM1']], [i['DIFFATOM'], i['CONSATOM2']]])
elif 'CONSATOM3' in i:
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
dyn.run(fmax=-i['EDIFFG'])
if iterate:
    print('Converged')
    atoms = read('POSCAR')  # type: Atoms
    dyn = Optimizer(atoms, trajectory='run.traj', restart='history.pckl')
    dyn.run(fmax=-i['EDIFFG'])
    c = iterate()
print('Done')
{% endblock python %}
