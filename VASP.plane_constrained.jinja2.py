{% extends "VASP.base.jinja2.sh" %}

{% block environment %}
source ~/.bashrc_vasp
export OMP_NUM_THREADS={{ openmp }}
export VASP_PROCS={{ tasks }}
{% endblock environment %}

{% block python %}
from custodian.custodian import *
from Classes_Custodian import *
import Upgrade_Run
import logging
import copy
import subprocess

from Classes_ASE import StandardVasp as Vasp
from Classes_Pymatgen import Incar
from ase.io import read
from ase.optimize.precon import PreconFIRE as FIRE
import numpy as np
import pdb

class InPlane:
    def __init__(self, diffusing_i, plane_i):
        self.diffusing_i = diffusing_i
        self.plane_i = plane_i

    def adjust_positions(self, oldpositions, newpositions):
        # get Normal Vector
        p1 = newpositions[self.plane_i[0]] # type: np.array
        p2 = newpositions[self.plane_i[1]] # type: np.array
        p3 = newpositions[self.plane_i[2]] # type: np.array
        v1 = p2 - p1
        v2 = p3 - p1

        # Get equation of plane ax+by+cz+d = 0
        normal = np.cross(v1, v2)
        a = normal[0]
        b = normal[1]
        c = normal[2]
        d = -(a*p1[0] + b*p1[1] + c*p1[2])

        # Get closest point on plane
        p = newpositions[self.diffusing_i]
        x = - (d + a*p[0] + b*p[1] + c*p[2]) / (a**2 + b**2 + c**2)
        position = [p[0] + x*a, p[1] + x*b, p[2] + x*c]
        newpositions[self.diffusing_i] = position

    def adjust_forces(self, atoms, forces):
        # get Normal Vector
        p1 = atoms.positions[self.plane_i[0]] # type: np.array
        p2 = atoms.positions[self.plane_i[1]] # type: np.array
        p3 = atoms.positions[self.plane_i[2]] # type: np.array
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2) / np.linalg.norm(np.cross(v1,v2))

        # Get equation of plane ax+by+cz+d = 0
        perp_projection = np.dot(normal, forces[self.diffusing_i] ) * normal
        pdb.set_trace()
        forces[self.diffusing_i] = forces[self.diffusing_i] - perp_projection

class InvertPlane:
    def __init__(self, diffusing_i, plane_i):
        self.diffusing_i = diffusing_i
        self.plane_i = plane_i

    def adjust_positions(self, oldpositions, newpositions):
        return

    def adjust_forces(self, atoms, forces):
        # get Normal Vector
        p1 = atoms.positions[self.plane_i[0]] # type: np.array
        p2 = atoms.positions[self.plane_i[1]] # type: np.array
        p3 = atoms.positions[self.plane_i[2]] # type: np.array
        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2) / np.linalg.norm(np.cross(v1,v2))

        # Get equation of plane ax+by+cz+d = 0
        perp_projection = 2 * np.dot(normal, forces[self.diffusing_i] ) * normal # Invert Forces
        pdb.set_trace()
        forces[self.diffusing_i] = forces[self.diffusing_i] - perp_projection

atoms = read('POSCAR')
atoms.set_calculator(Vasp())
i = Incar.from_file('INCAR')
i['NSW'] = 0
i['IBRION'] = -1
if 'IOPT' in i:
    del i['IOPT']
i.write_file('INCAR')
c = InPlane(i['DIFFATOM'], (i['CONSATOM1'], i['CONSATOM2'], i['CONSATOM3']))
atoms.set_constraint(c)

dyn = FIRE(atoms)
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
