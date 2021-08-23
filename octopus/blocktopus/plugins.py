from twisted.logger import Logger
from pathlib import Path
from typing import List

import sys
if sys.version_info < (3, 8):
    # https://packaging.python.org/guides/creating-and-discovering-plugins/
    # Actually 3.8 is the minimum version for importlib.metadata
    import importlib_metadata
else:
    import importlib.metadata as importlib_metadata

log = Logger()

BLOCKS_ENTRY_POINT = 'blocktopus_blocks'
BLOCKTOPUS_DIR = Path(__file__).resolve().parent.parent / 'octopus' / 'blocktopus'

def add_plugins_dir(plugins_dir: Path):
    """
    Add a directory contining plugins. Allows plugins to be stored locally for development
    rather than having to be installed.

    Any folder within the directory that is a python distribution (has a setup.py file)
    will be analysed, and any 'blocktopus_blocks' entry points will be registered as blocks.
    """
    import sys
    
    import setuptools
    from distutils.core import run_setup
    from importlib import import_module
    from .block_registry import register_block

    if not plugins_dir.is_dir():
        log.warn("Plugins directory {plugin_dir} not found.", plugin_dir=plugins_dir)
        return

    for child_dir in plugins_dir.iterdir():
        setup_file = child_dir / 'setup.py'

        if not setup_file.is_file():
            continue

        log.info("Adding plugin directory {plugin_dir} to sys.path", plugin_dir=child_dir)
        sys.path.append(str(child_dir))

        setup_result = run_setup(setup_file, stop_after='init')

        if setup_result.entry_points is None or BLOCKS_ENTRY_POINT not in setup_result.entry_points:
            continue

        for entry_point in setup_result.entry_points[BLOCKS_ENTRY_POINT]:
            ep_name, ep_value = entry_point.split('=', 1)
            entry_point = importlib_metadata.EntryPoint(ep_name.strip(), ep_value.strip(), BLOCKS_ENTRY_POINT)
            block_cls = entry_point.load()
            
            log.info(
                "Found local plugin entry-point block definition {block_name} {block_cls}",
                entry_point=entry_point,
                block_name=block_cls.__name__, 
                block_cls=block_cls,
            )

            register_block(block_cls.__name__, block_cls)


def register_installed_entrypoint_blocks():
    """
    Load and register any blocks that are exposed by the 'blocktopus_blocks' entry point in 
    any installed Python package.

    https://packaging.python.org/guides/creating-and-discovering-plugins/#using-package-metadata
    """

    from .block_registry import register_block

    entry_points = importlib_metadata.entry_points()

    if BLOCKS_ENTRY_POINT not in entry_points:
        return

    for entry_point in entry_points[BLOCKS_ENTRY_POINT]:
        block_cls = entry_point.load()

        log.info(
            "Found installed plugin entry-point block definition {block_name} {block_cls}",
            entry_point=entry_point,
            block_name=block_cls.__name__, 
            block_cls=block_cls,
        )

        register_block(block_cls.__name__, block_cls)


def get_block_plugin_modules():
    """
    (To be deprecated) Find all packages under octopus.blocks.
    """
    # Add plugin machine blocks
    # https://packaging.python.org/guides/creating-and-discovering-plugins/
    import importlib
    import pkgutil
    import octopus.blocks

    def iter_namespace(ns_pkg):
        # Specifying the second argument (prefix) to iter_modules makes the
        # returned name an absolute name instead of a relative one. This allows
        # import_module to work without having to do additional modification to
        # the name.
        return pkgutil.walk_packages(ns_pkg.__path__, ns_pkg.__name__ + ".")

    return {
        name: importlib.import_module(name)
        for finder, name, ispkg
        in iter_namespace(octopus.blocks)
    }


def get_block_plugin_block_names(check_subclass: type) -> List[str]:
    """
    Return a list of names of block classes within the octopus.blocks namespace
    that are subclasses of the passed check_subclass, but are not check_subclass
    itself.
    """
    return [
        name 
        for mod in get_block_plugin_modules().values()
        for name, cls in mod.__dict__.items() 
        if isinstance(cls, type) 
            and issubclass(cls, check_subclass)
            and cls is not check_subclass
    ]


def _subclasses(cls):
    return cls.__subclasses__() + [
        g for s in cls.__subclasses__()
        for g in _subclasses(s)
    ]


def get_machine_js_definitions():
    from octopus.blocktopus.blocks.machines import machine_declaration

    for block_cls in _subclasses(machine_declaration):
        try:
            yield (block_cls.__name__, block_cls.get_interface_definition())
        except AttributeError:
            pass


def get_connection_js_definitions():
    from octopus.blocktopus.blocks.machines import connection_declaration

    for connection_cls in _subclasses(connection_declaration):
        try:
            yield (connection_cls.__name__, connection_cls.get_interface_definition())
        except AttributeError:
            pass


def build_machine_block_definition_js(filename):
    import json

    with open(filename, 'w') as fp:
        fp.write("// Auto-generated file\n\n")

        for name, definition in get_machine_js_definitions():
            fp.write(f"Blockly.Blocks.addMachineBlock('{name}', {json.dumps(definition)});\n")


def build_connection_block_definition_js(filename):
    import json

    with open(filename, 'w') as fp:
        fp.write("// Auto-generated file\n\n")

        for name, definition in get_connection_js_definitions():
            fp.write(f"Blockly.Blocks.addConnectionBlock('{name}', {json.dumps(definition)});\n")
