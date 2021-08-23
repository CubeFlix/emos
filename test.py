

# TESTING

if __name__ == '__main__':
	from emos import *
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
	screenperipheral = ScreenPeripheral(computer, 1048, 768)
	computer.add_peripheral(screenperipheral)
	computer.start()

