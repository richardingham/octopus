cd /workspaces/octopus
pip install -e .
export NODE_PATH=$(npm root --quiet -g)
rollup -c
python tools/build.py
pip install bcrypt
