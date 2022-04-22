#!/bin/bash
 
# --------------------------------------------------------------
### PART 1: Requests resources to run your job.
# --------------------------------------------------------------

### Optional. Set the job name
#SBATCH --job-name=falco
### Optional. Set the output filename. SLURM reads %x as the job name and %j as the job ID
#SBATCH --output=%x-%j.out
### REQUIRED. Specify the PI group for this job
#SBATCH --account=UASAL
### Optional. Request email when job begins and ends
#SBATCH --mail-type=ALL
### Optional. Specify email address to use for notification
#SBATCH --mail-user=kianmilani@email.arizona.edu
### REQUIRED. Set the partition for your job.
#SBATCH --partition=standard
### REQUIRED. Set the number of cores that will be used for this job.
#SBATCH --ntasks=32
### REQUIRED. Set the number of nodes
#SBATCH --nodes=1
### REQUIRED. Set the memory required for this job.
#SBATCH --mem=64gb
### REQUIRED. Specify the time required for this job, hhh:mm:ss
#SBATCH --time=2:00:00

# --------------------------------------------------------------
### PART 2: Executes bash commands to run your job
# --------------------------------------------------------------

cd ~/Documents/falco-roman-cgi-dark-holes
conda init bash
source ~/.bashrc
conda activate poppy-env
python run_falco_hlc_band1_config.py

