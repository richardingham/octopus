
from twisted.logger import Logger
from pathlib import Path

log = Logger()

blocktopus_dir = Path(__file__).resolve().parent.parent / 'octopus' / 'blocktopus'

def add_plugins_dir(plugins_dir: Path):
    import sys
    
    import setuptools
    from distutils.core import run_setup 
    from importlib import import_module
    from .block_registry import register_block

    for child_dir in plugins_dir.iterdir():
        setup_file = child_dir / 'setup.py'

        if not setup_file.is_file():
            continue

        log.info("Adding plugin directory {plugin_dir} to sys.path", plugin_dir=child_dir)
        sys.path.append(child_dir)

        setup_result = run_setup(setup_file, stop_after='init')

        if setup_result.entry_points is None or 'blocktopus_blocks' not in setup_result.entry_points:
            continue

        for entry_point in setup_result.entry_points['blocktopus_blocks']:
            block_name, target = entry_point.split('=', 1)
            mod_name, obj_name = target.split(':', 1)

            mod = import_module(mod_name.strip())
            obj = mod

            obj_name_parts = obj_name.split('.')
            for part in obj_name_parts:
                obj = getattr(obj, part.strip())
            
            log.info(
                "Found entry-point block definition {block_name} {block_cls}",
                block_name=block_name, 
                block_cls=obj,
            )

            register_block(obj.__name__, obj)


def get_block_plugin_modules():
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


def get_block_plugin_block_names(check_subclass):
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
