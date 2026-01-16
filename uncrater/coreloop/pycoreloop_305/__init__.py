from . import core_loop as pystruct
from . import core_loop_errors as _errors
from . import lusee_commands as command

command_from_value, value_from_command = {}, {}
for name in dir(command):
    if name[0]=="_":
        continue
    value = getattr(command, name)
    command_from_value [value] = name
    value_from_command [name] = value

from . import lusee_appIds as appId
appId_from_value, value_from_appId = {}, {}
for name in dir(appId):
    if name[0]=="_":
        continue
    value = getattr(appId, name)
    appId_from_value [value] = name
    value_from_appId [name] = value

error_bits = {}
for i in range(32):
    error_bits [1<<i] = f"RESERVED"
for k,v in vars(_errors).items():
    if type(v)==int and v in error_bits:
        error_bits[v] = k

# dict that maps format code (str) to format value (int)
value_from_format = { name: getattr(pystruct, name)
                         for name in dir(pystruct)
                         if name.startswith("OUTPUT_") }

# dict that maps format value (int) to format code (str)
format_from_value = { getattr(pystruct, name): name
                         for name in dir(pystruct)
                         if name.startswith("OUTPUT_") }
