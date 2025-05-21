#!/bin/bash
cd ~/dancing-stick-figures
source venv/bin/activate

# Make sure the SSH agent is running and has your key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

python dancing_stick_figures.py --daily >> ~/dancing-stick-figures/cron.log 2>&1

# Kill the SSH agent when done
ssh-agent -k
