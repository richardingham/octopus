import sys
import os

plugins_dir = sys.argv[1]
packages_dir = sys.argv[2]

for plugin_name in os.listdir(plugins_dir):
    plugin_path = os.path.abspath(os.path.join(plugins_dir, plugin_name))

    print(f"{plugin_path} >> {os.path.join(packages_dir, plugin_name + '.pth')}")

    with open(os.path.join(packages_dir, plugin_name + '.pth'), 'w') as fp:
        fp.write(plugin_path)