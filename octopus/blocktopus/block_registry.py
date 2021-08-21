
from typing import Type
from types import ModuleType
from octopus.blocktopus.workspace import Block

from twisted.logger import Logger
log = Logger()


block_types = {}
exclude = set([Block])
processed = set()


def register_builtin_blocks():
    from octopus.blocktopus import blocks
    import importlib
    
    for mod_name in blocks.__all__:
        mod = importlib.import_module(f".{mod_name}", blocks.__name__)
        register_module_blocks(mod)
        

def register_module_blocks(mod: ModuleType):
    log.debug("Registering blocks from module {module}", module=mod)

    mod_dict = { name: cls for name, cls in mod.__dict__.items() if isinstance(cls, type) and issubclass(cls, Block) and cls not in processed }
    
    if "__all__" in mod.__dict__:
        exclude.update([cls for name, cls in mod_dict.items() if name not in mod.__all__])
        mod_dict = { name: cls for name, cls in mod_dict.items() if name in mod.__all__ }
    
    if "__exclude_blocks__" in mod.__dict__:
        exclude.update([cls for name, cls in mod_dict.items() if name in mod.__exclude_blocks__])

    for name, cls in mod_dict.items(): 
        if isinstance(cls, type) and issubclass(cls, Block) and cls not in exclude:
            register_block(name, cls)
    
    processed.update(mod_dict.values())


def register_block(name: str, block: Type[Block]):
    if name in block_types:
        raise ValueError(f"Block type {name} is already registered ({block_types[name]}).")

    log.debug("Registering block {block_name} as {block_cls}", block_name=name, block_cls=block)
    block_types[name] = block


def get_block_class(name: str) -> Type[Block]:
    return block_types[name]
