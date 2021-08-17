"""

- EMOS Main Source Code -

(C) Cubeflix 2021 (EMOS)

"""


# Imports
from misc import *
from memory import *
from cpu import *
from operatingsystem import *
from computer import *




# TESTING

memory = Memory()
computer = Computer()
computer.set_memory(memory)
operatingsystem = OperatingSystem(computer)
terminalscreen = TerminalScreen(computer)
harddrive = FileSystem(computer, "test.fs")
harddrive._backend_load()
harddrive._backend_update()
computer.set_filesystem(harddrive)
computer.add_peripheral(terminalscreen)
computer.set_os(operatingsystem)
cpu = CPU(computer, memory)
computer.set_cpu(cpu)
core = CPUCore(cpu)
cid = cpu.add_core(core)
core2 = CPUCore(cpu)
cid2 = cpu.add_core(core2)
cmdhandler = CMDHandler('')
cmdhandler.initialize(computer)
operatingsystem.set_cmd_handler(cmdhandler)
computer.start()