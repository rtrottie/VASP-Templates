#!/bin/bash
{% if queue_type == "slurm" and computer == "eagle" %}#SBATCH -J {{ name }}
#SBATCH --time={{ time }}:00:00
#SBATCH -o {{ name }}.o%j
#SBATCH -e {{ name }}.e%j
#SBATCH --mem={{ mem }}
#SBATCH --account={{ account }}
#SBATCH --tasks {{ tasks }}
{% if nodes == 1 and computer == "janus"%}#SBATCH --reservation=janus-serial {% endif %}
{% if computer == "summit" %}#SBATCH --qos {{ queue }}
#SBATCH -N {{ nodes }} {% endif %}
{% elif queue_type == "pbs" %}#PBS -j eo
#PBS -l nodes={{ nodes }}:ppn={{ ppn }}{% if computer == "psiops" %}:{{ queue }}{% endif %}
#PBS -l walltime={{ time }}:00:00
#PBS -q {% if computer == "psiops" %}batch{% else %}{{ queue }}{% endif %}
#PBS -N {{ name }}
{% if computer == "peregrine" %}#PBS -A {{ account }}{% endif %}
cd $PBS_O_WORKDIR
echo $PBS_O_WORKDIR{% endif %}

{% block environment %}
# Set Environment
source {{ vasp_bashrc }}
export OMP_NUM_THREADS={{ openmp }} {% endblock environment %}

{% block vasp %}
python -c "
{% block python %}
from custodian.vasp.jobs import *
from custodian.vasp.handlers import *
from custodian.custodian import *
from Classes_Custodian import *

incar = Incar.from_file('INCAR')

if 'AUTO_GAMMA' in incar and incar['AUTO_GAMMA']:
    vasp = '{{ vasp_gamma }}'
else:
    vasp = '{{ vasp_kpts }}'

vaspjob = [{{ jobtype }}Job(['{{ mpi }}', '-np', '{{ tasks }}', vasp], '{{ logname }}', auto_npar=False, backup=False)]

{% if jobtype == "NEB" %}
handlers = [WalltimeHandler({{ time }}*60*60, 15*60)]

{% elif jobtype == "Dimer" %}
handlers = [WalltimeHandler({{ time }}*60*60, 15*60), NEBNotTerminating('{{ logname }}', 180*60),
            DimerDivergingHandler(), DimerCheckMins(), UnconvergedErrorHandler()]

{% elif jobtype == "Standard" %}
handlers = [WalltimeHandler({{ time }}*60*60), UnconvergedErrorHandler()]
{% endif %}

c = Custodian(handlers, vaspjob, max_errors=10)
c.run()
{% endblock python %}
"
{% endblock vasp %}
