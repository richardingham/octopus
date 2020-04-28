cd /workspaces/octopus
pip install -e .
export NODE_PATH=$(npm root --quiet -g)
npm install -g @rollup/plugin-multi-entry
npm install -g rollup-plugin-node-builtins
rollup -c
python tools/build.py
pip install bcrypt

for dir in /workspaces/octopus-plugins/*/     # list directories in the form "/tmp/dirname/"
do
    pip install -e ${dir%*/}      # remove the trailing "/"
done