"""

- EMOS 'cpu.py' Source Code -

(C) Cubeflix 2021 (EMOS)

"""


# Imports
from .misc import *
from .memory import *


class Register:

	"""A CPU register."""

	def __init__(self, name, size):

		"""Create the register.
		   Args: name -> name of the register
		         size -> size of the register"""

		self.name = name
		self.size = size

	def initialize(self):

		"""Initialize the register."""

		self.data = bytearray(self.size)
		return (0, None)

	def finish(self):

		"""Clean up and finish using the register."""

		del self.data
		return (0, None)

	def set_data(self, data, offset):

		"""Set the data."""

		if not len(data) + offset <= self.size:
			return (1, "Length of data plus offset must be " + str(self.size) + " bits or less long.")
		self.data = bytearray(self.data[ : offset]) + bytearray(data) + bytearray(self.data[offset + len(data) : ])
		return (0, None)

	def get_byte(self, offset, baseoffset=0):

		"""Get byte offset from the register."""

		if offset + baseoffset < self.size:
			return (0, self.data[offset + baseoffset])
		else:
			return (2, "Offset out of range.")

	def get_bytes(self, offset, numbytes, baseoffset=0):

		"""Get numbytes bytes offset from the register."""

		finalbytes = bytearray(numbytes)
		for i in range(numbytes):
			exitcode, data = self.get_byte(i + offset, baseoffset)
			if exitcode != 0:
				return (exitcode, data)
			else:
				finalbytes[i] = data

		return (0, finalbytes)

	def __repr__(self):

		"""Get the string representation of the register."""

		if hasattr(self, 'data'):
			return "<Register " + self.name + " " + hex(int.from_bytes(self.data, byteorder='little')) + ">"
		else:
			return "<Register " + self.name + " None>"

	def __str__(self):

		"""Get the string representation of the register."""

		return self.__repr__()


class CPUCore:

	"""The main 32 bit CPU core class."""
	
	def __init__(self, cpu):

		"""Create the CPU core.
		   Args: cpu -> the CPU the core is attached to"""

		self.cpu = cpu
		self.alu = ALU()
		self.fpu = FPU()

	def initialize(self, processmemory, name, tid):

		"""Initialize the CPU core for running code.
		   Args: processmemory -> processmemory for the core to run
		         name -> the name of the processmemory segment in the main memory in the CPU
		         tid -> the thread number"""

		self.processmemory = processmemory
		self.pname = name
		self.tid = tid

		self.registers = {'RAX' : Register('RAX', 8), # RAX (Accumulator register)
						  'RCX' : Register('RCX', 8), # RCX (Count register)
						  'RDX' : Register('RDX', 8), # RDX (Data register)
						  'RBX' : Register('RBX', 8), # RBX (Base register)
						  'RSP' : Register('RSP', 8), # RSP (SP for stack pointer) NOTE: needs to be updated during runtime
						  'RBP' : Register('RBP', 8), # RBP (BP for base pointer) NOTE: updated by the user
						  'RSI' : Register('RSI', 8), # RSI (SI for source index)
						  'RDI' : Register('RDI', 8), # RDI (DI for destination index)
						  'RIP' : Register('RIP', 8), # RIP (IP for instruction pointer) NOTE: needs to be updated during runtime
						  'RCS' : Register('CS', 8),  # Code segment
						  'RDS' : Register('DS', 8),  # Data segment
						  'RSS' : Register('SS', 8),  # Stack segment
						  'RES' : Register('ES', 8),  # Ending segment NOTE: needs to be updated during runtime
						  'RFLAGS' : Register('FLAGS', 8)} # Flags register NOTE: needs to be updated during runtime
						  # FLAGS: 
						  # 0 -> carry
						  # 1 -> overflow
						  # 2 -> parity
						  # 3 -> zero
						  # 4 -> sign
						  # 5 -> less than
						  # 6 -> greater than
						  # 7 -> equal

		for i in range(8, 16):
			self.registers['R' + str(i)] = Register('R' + str(i), 8)

		for register in self.registers:
			self.registers[register].initialize()
			
		self.registers['RCS'].set_data(int.to_bytes(processmemory.cs, 4, byteorder='little'), 4)
		self.registers['RDS'].set_data(int.to_bytes(processmemory.ds, 4, byteorder='little'), 4)
		self.registers['RSS'].set_data(int.to_bytes(processmemory.ss, 4, byteorder='little'), 4)
		self.registers['RES'].set_data(int.to_bytes(processmemory.es, 4, byteorder='little'), 4)

		self.registers['RSP'].set_data(int.to_bytes(processmemory.ss, 4, byteorder='little'), 4)
		self.registers['RBP'].set_data(int.to_bytes(processmemory.ss, 4, byteorder='little'), 4)

		self.error = False

	def get(self, src):

		"""Get data from registers, memory, or a constant using a src tuple with type and metadata.
		   Args: src -> a tuple with the type and data.
		   If src[0] is 'reg', src[1][0] will be the register suffix, src[1][1] will be the register start offset, and src[1][2] will be the length of the data.
		   If src[0] is 'mem', src[1][0] will be the memory offset, and src[1][1] will be the length of the data to get.
		   If src[0] is 'const', src[1][0] will be the data as a constant"""

		# Get source data
		srctype = src[0].lower()

		if srctype == 'reg':
			# Register source
			srcregsuffix = src[1][0].upper()
			srcregstart = int.from_bytes(src[1][1], byteorder='little')
			srcreglen = int.from_bytes(src[1][2], byteorder='little')

			srcexitcode, srcdata = self.registers['R' + srcregsuffix].get_bytes(0, srcreglen, srcregstart)
			return (srcexitcode, srcdata)
		elif srctype == 'mem':
			# Memory source
			srcoffset = int.from_bytes(src[1][0], byteorder='little')
			srclength = int.from_bytes(src[1][1], byteorder='little')
			# Update the memory
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			srcexitcode, srcdata = self.processmemory.get_bytes(srcoffset, srclength)
			return (srcexitcode, srcdata)
		elif srctype == 'const':
			# Constant value
			srcexitcode = 0
			srcdata = src[1][0]
			return (srcexitcode, srcdata)
		elif srctype == 'heap':
			# Heap memory destination
			memId = int.from_bytes(src[1][0], byteorder='little')
			memOffset = int.from_bytes(src[1][1], byteorder='little')
			memSize = int.from_bytes(src[1][2], byteorder='little')
			return self.cpu.computer.operatingsystem.get_memory(memId, memOffset, memSize)
		elif srctype == 'perp':
			# Peripheral memory source
			memId = int.from_bytes(src[1][0], byteorder='little')
			memOffset = int.from_bytes(src[1][1], byteorder='little')
			memSize = int.from_bytes(src[1][2], byteorder='little')

			if not ('perp', memId) in self.cpu.computer.memory.memorypartitions:
				return (23, "Memory ID is not in the computer memory.")

			memPart = self.cpu.computer.memory.memorypartitions[('perp', memId)]

			if memOffset + memSize > memPart.size or memSize != len(srcdata):
				return (17, "Memory out of range.")

			newData = memPart.data[memOffset : memOffset + memSize]

			return (0, newData)
		elif srctype == 'pmem':
			# Get a different processes memory
			memId = int.from_bytes(src[1][0], byteorder='little')
			memOffset = int.from_bytes(src[1][1], byteorder='little')
			memSize = int.from_bytes(src[1][2], byteorder='little')

			if destlength != len(srcdata) or self.cpu.computer.memory.memorypartitions[('proc', memId)].ss < memOffset:
				return (17, "Memory section is not large enough to hold given data.")

			if not ('proc', memId) in self.cpu.computer.memory.memorypartitions:
				return (23, "Memory ID is not in the computer memory.")

			srcexitcode, msg = self.cpu.computer.memory.memorypartitions[('proc', memId)].get_bytes(srcdata, destoffset)
			if srcexitcode != 0:
				return (srcexitcode, msg)

			return (0, msg)
		else:
			return (14, "Not a supported source data type.")

	def set(self, srcdata, dest):

		"""Set data to a register, or memory using dest.
		   Args: srcdata -> bytes like object to put at dest
		   		 dest -> the destination tuple with the type and data
		   		 If dest[0] is 'reg', then dest[1][0] will be the register suffix, dest[1][1] will be the register start position, and dest[1][2] will be the size of the data.
		   		 If dest[0] is 'mem', then dest[1][0] will be the starting offset to place srcdata at, and dest[1][1] will be the ending offset minus the starting offset"""

		desttype = dest[0].lower()

		# Move to destination
		if desttype == 'reg':
			# Move to register
			destregsuffix = dest[1][0].upper()
			destregstart = int.from_bytes(dest[1][1], byteorder='little')
			destreglen = int.from_bytes(dest[1][2], byteorder='little')

			if destreglen != len(srcdata):
				return (16, "Register section is not large enough to hold given data.")

			destexitcode, msg = self.registers['R' + destregsuffix].set_data(srcdata, destregstart)

			return (destexitcode, msg)
		elif desttype == 'mem':
			# Move to memory
			destoffset = int.from_bytes(dest[1][0], byteorder='little')
			destlength = int.from_bytes(dest[1][1], byteorder='little')

			if destlength != len(srcdata):
				return (17, "Memory section is not large enough to hold given data.")

			destexitcode, msg = self.processmemory.set_bytes(srcdata, destoffset)
			if destexitcode != 0:
				return (destexitcode, msg)

			self.registers['RES'].data[4 : 8] = int.to_bytes(self.processmemory.es, 4, byteorder='little')

			# Update the memory
			self.cpu.memory.edit_memory_partition(self.pname, self.processmemory)
			self.cpu.computer.memory.edit_memory_partition(self.pname, self.processmemory)
			self.cpu.computer.operatingsystem.processes[self.pname[1]].processmemory = self.processmemory
			self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].stack = self.processmemory.stack

			return (destexitcode, msg)
		elif desttype == 'heap':
			# Heap memory destination
			memId = int.from_bytes(dest[1][0], byteorder='little')
			memOffset = int.from_bytes(dest[1][1], byteorder='little')
			memSize = int.from_bytes(dest[1][2], byteorder='little')
			return self.cpu.computer.operatingsystem.edit_memory(memId, srcdata, memOffset)
		elif desttype == 'perp':
			# Peripheral memory destination
			memId = int.from_bytes(dest[1][0], byteorder='little')
			memOffset = int.from_bytes(dest[1][1], byteorder='little')
			memSize = int.from_bytes(dest[1][2], byteorder='little')

			if not ('perp', memId) in self.cpu.computer.memory.memorypartitions:
				return (23, "Memory ID is not in the computer memory.")

			memPart = self.cpu.computer.memory.memorypartitions[('perp', memId)]

			if memOffset + memSize > memPart.size or memSize != len(srcdata):
				return (17, "Memory section is not large enough to hold given data.")

			newData = memPart.data[ : memOffset] + srcdata + memPart.data[memOffset + memSize : ]
			return self.cpu.computer.memory.memorypartitions[('perp', memId)].set_data(newData)
		elif desttype == 'pmem':
			# Different processes memory destination
			# Check the process security level
			if self.cpu.computer.operatingsystem.processes[self.pname[1]].security_level == 1:
				return (40, "Invalid process security level.")
			memId = int.from_bytes(dest[1][0], byteorder='little')
			memOffset = int.from_bytes(dest[1][1], byteorder='little')
			memSize = int.from_bytes(dest[1][2], byteorder='little')

			if destlength != len(srcdata) or self.cpu.computer.memory.memorypartitions[('proc', memId)].ss < memOffset:
				return (17, "Memory section is not large enough to hold given data.")

			if not ('proc', memId) in self.cpu.computer.memory.memorypartitions:
				return (23, "Memory ID is not in the computer memory.")

			destexitcode, msg = self.cpu.computer.memory.memorypartitions[('proc', memId)].set_bytes(srcdata, destoffset)
			if destexitcode != 0:
				return (destexitcode, msg)

			# Update cores
			for cid, cpu in self.cpu.cores.items():
				if hasattr(cpu, 'processmemory'):
					try:
						if cpu.pname[1] == self.pname[1]:
							cpu.processmemory.data = self.cpu.computer.memory.memorypartitions[('proc', memId)].data
					except Exception:
						pass
			# Update process processmemory
			self.cpu.computer.operatingsystem.processes[self.pname[1]].data = self.cpu.computer.memory.memorypartitions[('proc', memId)].data
			return (0, None)
		else:
			return (15, "Not a supported destination type.")

	def move(self, dest, src):

		"""Move src into dest.
		   Args: dest -> the destination to move to, which is a tuple with the type and data.
		   		 src -> the source to move from, which is a tuple with the type and data."""

		# Get source data
		srcexitcode, srcdata = self.get(src)

		if srcexitcode != 0:
			return (srcexitcode, srcdata)

		# Set destination data
		destexitcode, msg = self.set(srcdata, dest)

		if destexitcode != 0:
			return (destexitcode, msg)

		return (0, None)

	def pop(self, dest):

		"""Pop the stack and save it into dest.
		   Args: dest -> destination tuple"""

		exitcode, data = self.processmemory.pop_stack()
		# Update the memory
		self.cpu.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.operatingsystem.processes[self.pname[1]].processmemory = self.processmemory
		self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].stack = self.processmemory.stack

		if exitcode != 0:
			return (exitcode, data)

		self.registers['RES'].data[4 : 8] = int.to_bytes(int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') - 4, 4, byteorder='little')

		exitcode, msg = self.set(data, dest)
		return (exitcode, msg)

	def push(self, src):

		"""Push src onto the stack.
		   Args: src -> source tuple"""

		exitcode, data = self.get(src)
		if exitcode != 0:
			return (exitcode, data)

		self.registers['RES'].data[4 : 8] = int.to_bytes(int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') + 4, 4, byteorder='little')

		exitcode, msg = self.processmemory.push_stack(data)
		# Update the memory
		self.cpu.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.operatingsystem.processes[self.pname[1]].processmemory = self.processmemory
		self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].stack = self.processmemory.stack
		
		return (exitcode, msg)

	def add(self, src0, src1, dest, modflags=True):

		"""Use a binary add on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to add
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform addition
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.add(src0data, src1data, size)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[3] = (1 if int.from_bytes(answer, byteorder='little') == 0 else 0)
			self.registers['RFLAGS'].data[0] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def sub(self, src0, src1, dest, modflags=True):

		"""Use a binary subtract on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to subtract
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform subtraction
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.sub(src0data, src1data, size)

		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[3] = (1 if int.from_bytes(answer, byteorder='little', signed=True) == 0 else 0)
			self.registers['RFLAGS'].data[0] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def mul(self, src0, src1, dest, modflags=True):

		"""Use a binary unsigned multiply on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to multiply
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform multiplication
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.mul(src0data, src1data, size)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[3] = (1 if int.from_bytes(answer, byteorder='little') == 0 else 0)
			self.registers['RFLAGS'].data[0] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def mul_signed(self, src0, src1, dest, modflags=True):

		"""Use a binary signed multiply on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to multiply
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform multiplication
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.mul_signed(src0data, src1data, size)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[3] = (1 if int.from_bytes(answer, byteorder='little', signed=True) == 0 else 0)
			self.registers['RFLAGS'].data[1] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def div(self, src0, src1, dest0, dest1, modflags=True):

		"""Use a binary unsigned divide on src0 and src1 and save it to dest0, with the modulus at dest1.
		   Args: src0, src1: source tuples to divide
		   		 dest0 -> destination tuple for the answer
		   		 dest1 -> destination tuple for the modulus
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform division
		exitcode, size0 = getsize(dest0)
		if exitcode != 0:
			return (exitcode, size0)
		exitcode, size1 = getsize(dest1)
		if exitcode != 0:
			return (exitcode, size1)

		exitcode, answers = self.alu.div(src0data, src1data, size0, size1)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answers)

		answer0, answer1 = answers

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer0, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[3] = (1 if int.from_bytes(answer1, byteorder='little') == 0 else 0)
			self.registers['RFLAGS'].data[0] = 0

		exitcode, msg = self.set(answer0, dest0)
		if exitcode != 0:
			return (exitcode, msg)
		exitcode, msg = self.set(answer1, dest1)
		return (exitcode, msg)

	def div_signed(self, src0, src1, dest0, dest1, modflags=True):

		"""Use a binary signed divide on src0 and src1 and save it to dest0, with the modulus at dest1.
		   Args: src0, src1: source tuples to divide
		   		 dest0 -> destination tuple for the answer
		   		 dest1 -> destination tuple for the modulus
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform division
		size0 = getsize(dest0)
		size1 = getsize(dest1)

		exitcode, answers = self.alu.div_signed(src0data, src1data, size0, size1)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		answer0, answer1 = answers

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer0, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[3] = (1 if int.from_bytes(answer1, byteorder='little', signed=True) == 0 else 0)
			self.registers['RFLAGS'].data[0] = 0

		exitcode, msg = self.set(answer0, dest0)
		if exitcode != 0:
			return (exitcode, msg)
		exitcode, msg = self.set(answer1, dest1)
		return (exitcode, msg)

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def bit_and(self, src0, src1, dest, modflags=True):

		"""Use a binary and on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to AND
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform AND gate
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.bit_and(src0data, src1data, size)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[1] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def bit_or(self, src0, src1, dest, modflags=True):

		"""Use a binary or on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to OR
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform OR gate
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.bit_or(src0data, src1data, size)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[1] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def bit_xor(self, src0, src1, dest, modflags=True):

		"""Use a binary xor on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to XOR
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform XOR gate
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.bit_xor(src0data, src1data, size)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[1] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def bit_not(self, src0, dest, modflags=True):

		"""Use a binary not on src0 and save it to dest.
		   Args: src0: source tuple to OR
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		# Preform NOT gate
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.bit_not(src0data, size)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[1] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def jmp(self, addr):

		"""Preform a jump to addr by changing the instruction pointer.
		   Args: addr -> the address to jump to"""

		return self.registers['RIP'].set_data(self.handle_output(self.get(addr)), 4)

	def cmp(self, a, b):

		"""Compare a and b as unsigned integers and modify the correct flags.
		   Args: a -> tuple to a
		   		 b -> tuple to b"""

		a_int = int.from_bytes(self.handle_output(self.get(a)), byteorder='little')
		b_int = int.from_bytes(self.handle_output(self.get(b)), byteorder='little')

		self.handle_output(self.registers['RFLAGS'].set_data(b'\x00\x00\x00', 5))

		if a_int < b_int:
			# a is less than b
			return self.registers['RFLAGS'].set_data(b'\x01', 5)
		elif a_int > b_int:
			# a is larger than b
			return self.registers['RFLAGS'].set_data(b'\x01', 6)
		elif a_int == b_int:
			# a is equal to b
			return self.registers['RFLAGS'].set_data(b'\x01', 7)

	def cmp_signed(self, a, b):

		"""Compare a and b as signed integers and modify the correct flags.
		   Args: a -> tuple to a
		   		 b -> tuple to b"""

		a_int = int.from_bytes(self.handle_output(self.get(a)), byteorder='little', signed=True)
		b_int = int.from_bytes(self.handle_output(self.get(b)), byteorder='little', signed=True)

		self.handle_output(self.registers['RFLAGS'].set_data(b'\x00\x00\x00', 5))

		if a_int < b_int:
			# a is less than b
			return self.registers['RFLAGS'].set_data(b'\x01', 5)
		elif a_int > b_int:
			# a is larger than b
			return self.registers['RFLAGS'].set_data(b'\x01', 6)
		elif a_int == b_int:
			# a is equal to b
			return self.registers['RFLAGS'].set_data(b'\x01', 7)

	def jmp_less(self, addr):

		"""Jump to addr if the less than flag is on.
		   Args: addr -> the address to jump to if the less than flag is on"""

		if self.registers['RFLAGS'].data[5] == 1:
			return self.jmp(addr)
		return (0, None)

	def jmp_greater(self, addr):

		"""Jump to addr if the greater than flag is on.
		   Args: addr -> the address to jump to if the greater than flag is on"""

		if self.registers['RFLAGS'].data[6] == 1:
			return self.jmp(addr)
		return (0, None)

	def jmp_equal(self, addr):

		"""Jump to addr if the equal flag is on.
		   Args: addr -> the address to jump to if the equal flag is on"""

		if self.registers['RFLAGS'].data[7] == 1:
			return self.jmp(addr)
		return (0, None)

	def jmp_less_equal(self, addr):

		"""Jump to addr if the equal or less than flag is on.
		   Args: addr -> the address to jump to if the equal or less than flag is on"""

		if self.registers['RFLAGS'].data[7] == 1 or self.registers['RFLAGS'].data[5] == 1:
			return self.jmp(addr)
		return (0, None)

	def jmp_greater_equal(self, addr):

		"""Jump to addr if the equal or greater than flag is on.
		   Args: addr -> the address to jump to if the equal or greater than flag is on"""

		if self.registers['RFLAGS'].data[7] == 1 or self.registers['RFLAGS'].data[6] == 1:
			return self.jmp(addr)
		return (0, None)

	def jmp_not_equal(self, addr):

		"""Jump to addr if the equal flag is off.
		   Args: addr -> the address to jump to if the equal flag is off"""

		if not self.registers['RFLAGS'].data[7]:
			return self.jmp(addr)
		return (0, None)

	def no_op(self):

		"""No operation."""

		return (0, None)

	def halt(self, output):

		"""Halt the program."""

		output = int.from_bytes(self.handle_output(self.get(output)), byteorder='little')

		self.output_exit = (output, None)

		# Add the exitcode
		self.cpu.update_from_computer()
		self.processmemory = self.cpu.memory.memorypartitions[self.pname]
		self.set(int.to_bytes(output, 2, byteorder='little'), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([2]))))

		self.running = False

		return (0, None)

	def call(self, addr):

		"""Jump to address addr, and store the current RIP pointer in the stack.
		   Args: addr -> the address of the function"""

		# Push the next instruction pointer to go to
		self.handle_output(self.push(("REG", ("IP", bytes([4]), bytes([4])))))
		# Push the current base pointer to revert back to after
		self.handle_output(self.push(("REG", ("BP", bytes([4]), bytes([4])))))
		# Put the current RES into RBP so that the function knows where it's stack frame is
		self.handle_output(self.move(("REG", ("BP", bytes([4]), bytes([4]))), ("REG", ("ES", bytes([4]), bytes([4])))))
		# Jump to addr
		self.handle_output(self.jmp(addr))
		return (0, None)

	def ret(self):

		"""Return from the function."""

		# Get the stack pointer back into RBP
		self.handle_output(self.pop(("REG", ("BP", bytes([4]), bytes([4])))))
		# Get the instruction pointer back into RIP (basically JMP there)
		self.handle_output(self.pop(("REG", ("IP", bytes([4]), bytes([4])))))

		return (0, None)

	def systemcall(self):

		"""Call the operating system."""

		# Create and start the thread
		sthread = threading.Thread(target=self.cpu.computer.operatingsystem.systemcall, args=(self.pname[1], self.tid))
		sthread.start()
		# Raise an interrupt
		raise Interrupt()
		# No need to return, as the interrupt stops execution anyway

	def popn(self, dest, n):

		"""Pop the stack and save it into dest.
		   Args: dest -> destination tuple
		         n -> number of bytes to pop"""

		n = int.from_bytes(self.handle_output(self.get(n)), byteorder='little')
		exitcode, data = self.processmemory.popn_stack(n)
		# Update the memory
		self.cpu.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.operatingsystem.processes[self.pname[1]].processmemory = self.processmemory
		self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].stack = self.processmemory.stack
		if exitcode != 0:
			return (exitcode, data)

		self.registers['RES'].data[4 : 8] = int.to_bytes(int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') - n, 4, byteorder='little')

		exitcode, msg = self.set(data, dest)
		return (exitcode, msg)

	def pushn(self, src):

		"""Push src onto the stack.
		   Args: src -> source tuple"""

		exitcode, data = self.get(src)
		if exitcode != 0:
			return (exitcode, data)

		self.registers['RES'].data[4 : 8] = int.to_bytes(int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') + len(data), 4, byteorder='little')

		exitcode, msg = self.processmemory.pushn_stack(data)
		# Update the memory
		self.cpu.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.operatingsystem.processes[self.pname[1]].processmemory = self.processmemory
		self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].stack = self.processmemory.stack
		return (exitcode, msg)

	def inf_loop(self):

		"""Get into an infinite loop."""

		self.jmp(int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') - 1)

	def interrupt(self, iid):

		"""Call an interrupt with ID iid,
		   Args: iid -> interrupt ID to call."""

		# Create and start the thread
		sthread = threading.Thread(target=self.cpu.computer.operatingsystem.interrupt, args=(self.handle_output(self.get(iid)), self.pname[1], self.tid))
		sthread.start()
		# Raise an interrupt
		raise Interrupt()
		# No need to return, as the interrupt stops execution anyway

	def argn(self, dest, argnum):

		"""Get argument argnum from the stack, moving it to dest.
		   Args: dest -> destination to move the argument to
		         argnum -> the argument number to move"""

		# Get the argument number
		argnum = int.from_bytes(self.handle_output(self.get(argnum)), byteorder='little')
		# Get the position for the argument
		offset = int.from_bytes(self.registers['RBP'].data[4 : 8], byteorder='little') - (8 + 4 * (argnum + 1))
		if offset < self.processmemory.ss:
			return (2, "Offset not in stack range.")
		# Move the data
		return self.move(dest, ('mem', (int.to_bytes(offset, 4, byteorder='little'), b'\x04')))

	def call_library(self, lid, call):

		"""Call a library call with library ID lid, and call ID call,
		   Args: lid -> library ID to call.
		         call -> call ID to run"""

		# Create and start the thread
		sthread = threading.Thread(target=self.cpu.computer.operatingsystem.call_library, args=(self.pname[1], self.tid, self.handle_output(self.get(lid)), self.handle_output(self.get(call))))
		sthread.start()
		# Raise an interrupt
		raise Interrupt()
		# No need to return, as the interrupt stops execution anyway

	def bit_shift_left(self, src0, src1, dest, modflags=True, signed=False):

		"""Use a binary left shift on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to shift
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags
		   		 signed -> whether to use signed shifts"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform shift
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.bit_shift_left(src0data, src1data, size, signed)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[1] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def bit_shift_right(self, src0, src1, dest, modflags=True, signed=False):

		"""Use a binary right shift on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to shift
		   		 dest -> destination tuple
		   		 modflags -> whether to modify the flags
		   		 signed -> whether to use signed shifts"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform shift
		exitcode, size = getsize(dest)
		if exitcode != 0:
			return (exitcode, size)

		exitcode, answer = self.alu.bit_shift_right(src0data, src1data, size, signed)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[1] = 1
				return (exitcode, answer)

		if modflags:
			self.registers['RFLAGS'].data[2] = bin(int.from_bytes(answer, byteorder='little')).count('1') % 2
			self.registers['RFLAGS'].data[1] = 0

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def exit_if_rax(self):

		"""Exit the program if RAX is not 0. If so, exit with exitcode in RAX."""

		if self.registers['RAX'].data[ : 4] != b'\x00\x00\x00\x00':			
			return self.halt(('REG', ('AX', b'\x00', b'\x02')))

		return (0, None)

	def move_less(self, dest, src):

		"""Move if the less than flag is on.
		   Args: dest -> destination
		         src -> source"""

		if self.registers['RFLAGS'].data[5] == 1:
			return self.move(dest, src)
		return (0, None)

	def move_greater(self, dest, src):

		"""Move if the greater than flag is on.
		   Args: dest -> destination
		         src -> source"""

		if self.registers['RFLAGS'].data[6] == 1:
			return self.move(dest, src)
		return (0, None)

	def move_equal(self, dest, src):

		"""Move if the equal than flag is on.
		   Args: dest -> destination
		         src -> source"""

		if self.registers['RFLAGS'].data[7] == 1:
			return self.move(dest, src)
		return (0, None)

	def move_less_equal(self, dest, src):

		"""Move if the equal or less than flag is on.
		   Args: deat -> destination
		         src -> source"""

		if self.registers['RFLAGS'].data[7] == 1 or self.registers['RFLAGS'].data[5] == 1:
			return self.move(dest, src)
		return (0, None)

	def move_greater_equal(self, dest, src):

		"""Move if the equal or greater than flag is on.
		   Args: deat -> destination
		         src -> source"""

		if self.registers['RFLAGS'].data[7] == 1 or self.registers['RFLAGS'].data[6] == 1:
			return self.move(dest, src)
		return (0, None)

	def move_not_equal(self, dest, src):

		"""Move if the equal than flag is off.
		   Args: dest -> destination
		         src -> source"""

		if not self.registers['RFLAGS'].data[7] == 1:
			return self.move(dest, src)
		return (0, None)

	def pop_remove(self):

		"""Pop four bytes off the stack and remove them."""

		exitcode, data = self.processmemory.pop_stack()
		# Update the memory
		self.cpu.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.operatingsystem.processes[self.pname[1]].processmemory = self.processmemory
		self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].stack = self.processmemory.stack

		if exitcode != 0:
			return (exitcode, data)

		self.registers['RES'].data[4 : 8] = int.to_bytes(int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') - 4, 4, byteorder='little')

		return (0, None)

	def popn_remove(self, n):

		"""Pop N bytes off the stack and remove them.
		   Args: n -> number of bytes to pop"""

		n = int.from_bytes(self.handle_output(self.get(n)), byteorder='little')
		exitcode, data = self.processmemory.popn_stack(n)
		# Update the memory
		self.cpu.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.memory.edit_memory_partition(self.pname, self.processmemory)
		self.cpu.computer.operatingsystem.processes[self.pname[1]].processmemory = self.processmemory
		self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].stack = self.processmemory.stack
		if exitcode != 0:
			return (exitcode, data)

		self.registers['RES'].data[4 : 8] = int.to_bytes(int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') - n, 4, byteorder='little')

		return (0, None)

	def varn(self, dest, n):

		"""Get variable number N from the stack.
		   Args: dest -> destination
		         n -> variable number"""

		n = int.from_bytes(self.handle_output(self.get(n)), byteorder='little')
		# Get the offset and data
		offset = int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') - 4 * (n + 1)
		if offset < self.processmemory.ss:
			return (2, "Offset not in stack range.")
		# Move the data
		return self.move(dest, ('mem', (int.to_bytes(offset, 4, byteorder='little'), b'\x04')))

	def offset_get(self, dest, offset, n):

		"""Get N bytes from the position ES - offset, and put it into dest.
		   Args: dest -> destination
		         offset -> offset
		         n -> number of bytes"""

		n = self.handle_output(self.get(n))
		offset = int.from_bytes(self.handle_output(self.get(offset)), byteorder='little')
		offset = int.from_bytes(self.registers['RES'].data[4 : 8], byteorder='little') - offset
		if offset < 0:
			return (2, "Offset not in range.")
		# Move the data
		return self.move(dest, ('mem', (int.to_bytes(offset, 4, byteorder='little'), n)))

	def add_float(self, src0, src1, dest):

		"""Use a floating point add on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to add
		   		 dest -> destination tuple"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform addition
		exitcode, answer = self.fpu.add(src0data, src1data)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def sub_float(self, src0, src1, dest):

		"""Use a floating point subtract on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to subtract
		   		 dest -> destination tuple"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform addition
		exitcode, answer = self.fpu.sub(src0data, src1data)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def mul_float(self, src0, src1, dest):

		"""Use a floating point multiply on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to multiply
		   		 dest -> destination tuple"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform addition
		exitcode, answer = self.fpu.mul(src0data, src1data)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def div_float(self, src0, src1, dest):

		"""Use a floating point divide on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to divide
		   		 dest -> destination tuple"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform addition
		exitcode, answer = self.fpu.div(src0data, src1data)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def power_float(self, src0, src1, dest):

		"""Use a floating point divide on src0 and src1 and save it to dest.
		   Args: src0, src1: source tuples to raise
		   		 dest -> destination tuple"""

		# Get source data
		src0exitcode, src0data = self.get(src0)

		if src0exitcode != 0:
			return (src0exitcode, src0data)

		src1exitcode, src1data = self.get(src1)

		if src1exitcode != 0:
			return (src1exitcode, src1data)

		# Preform addition
		exitcode, answer = self.fpu.power(src0data, src1data)
		if exitcode != 0:
			if exitcode == 18:
				if modflags:
					self.registers['RFLAGS'].data[0] = 1
				return (exitcode, answer)

		exitcode, msg = self.set(answer, dest)
		return (exitcode, msg)

	def cmp_float(self, a, b):

		"""Compare a and b as floating point numbers and modify the correct flags.
		   Args: a -> tuple to a
		   		 b -> tuple to b"""

		a_int = struct.unpack('f', self.handle_output(self.get(a)))[0]
		b_int = struct.unpack('f', self.handle_output(self.get(b)))[0]

		self.handle_output(self.registers['RFLAGS'].set_data(b'\x00\x00\x00', 5))

		if a_int < b_int:
			# a is less than b
			return self.registers['RFLAGS'].set_data(b'\x01', 5)
		elif a_int > b_int:
			# a is larger than b
			return self.registers['RFLAGS'].set_data(b'\x01', 6)
		elif a_int == b_int:
			# a is equal to b
			return self.registers['RFLAGS'].set_data(b'\x01', 7)

	def int_to_float(self, src, dest):

		"""Convert src as a integer to a floating point number and put it into dest.
		   Args: src -> tuple to src
		         dest -> tuple to dest"""

		src_int = int.from_bytes(self.handle_output(self.get(src)), byteorder='little')
		dest_float = struct.pack('f', float(src_int))

		exitcode, msg = self.set(dest_float, dest)
		return (exitcode, msg)

	def signed_int_to_float(self, src, dest):

		"""Convert src as a signed integer to a floating point number and put it into dest.
		   Args: src -> tuple to src
		         dest -> tuple to dest"""

		src_int = int.from_bytes(self.handle_output(self.get(src)), byteorder='little', signed=True)
		dest_float = struct.pack('f', float(src_int))

		exitcode, msg = self.set(dest_float, dest)
		return (exitcode, msg)

	def float_to_int(self, src, dest):

		"""Convert src as a floating point number to an integer and put it into dest.
		   Args: src -> tuple to src
		         dest -> tuple to dest"""

		src_float = struct.unpack('f', self.handle_output(self.get(src)))[0]
		try:
			dest_int = int.from_bytes(int(src_int), byteorder='little')
		except Exception as e:
			return (18, "Overflow error.")

		exitcode, msg = self.set(dest_int, dest)
		return (exitcode, msg)

	def float_to_signed_int(self, src, dest):

		"""Convert src as a floating point number to an signed integer and put it into dest.
		   Args: src -> tuple to src
		         dest -> tuple to dest"""

		src_float = struct.unpack('f', self.handle_output(self.get(src)))[0]
		try:
			dest_int = int.from_bytes(int(src_int), byteorder='little', signed=True)
		except Exception as e:
			return (18, "Overflow error.")

		exitcode, msg = self.set(dest_int, dest)
		return (exitcode, msg)


	# Dictionary of all opcodes
	opcode_dict = {0 : (move, 2, {}),
				   1 : (add, 3, {}),
				   2 : (sub, 3, {}),
				   3 : (mul, 3, {}),
				   4 : (mul_signed, 3, {}),
				   5 : (div, 4, {}),
				   6 : (div_signed, 4, {}),
				   7 : (bit_and, 3, {}),
				   8 : (bit_or, 3, {}),
				   9 : (bit_xor, 3, {}),
				   10 : (bit_not, 2, {}),
				   11 : (push, 1, {}),
				   12 : (pop, 1, {}), 
				   13 : (add, 3, {'modflags' : False}),
				   14 : (sub, 3, {'modflags' : False}),
				   15 : (mul, 3, {'modflags' : False}),
				   16 : (mul_signed, 3, {'modflags' : False}),
				   17 : (div, 4, {'modflags' : False}),
				   18 : (div_signed, 4, {'modflags' : False}),
				   19 : (bit_and, 3, {'modflags' : False}),
				   20 : (bit_or, 3, {'modflags' : False}),
				   21 : (bit_xor, 3, {'modflags' : False}),
				   22 : (bit_not, 2, {'modflags' : False}),
				   23 : (jmp, 1, {}),
				   24 : (cmp, 2, {}),
				   25 : (cmp_signed, 2, {}),
				   26 : (jmp_less, 1, {}),
				   27 : (jmp_greater, 1, {}),
				   28 : (jmp_equal, 1, {}),
				   29 : (jmp_less_equal, 1, {}),
				   30 : (jmp_greater_equal, 1, {}),
				   31 : (jmp_not_equal, 1, {}),
				   32 : (no_op, 0, {}),
				   33 : (halt, 1, {}),
				   34 : (call, 1, {}),
				   35 : (ret, 0, {}),
				   36 : (systemcall, 0, {}),
				   37 : (popn, 2, {}),
				   38 : (pushn, 1, {}),
				   39 : (inf_loop, 0, {}),
				   40 : (interrupt, 1, {}),
				   41 : (argn, 2, {}),
				   42 : (call_library, 2, {}),
				   43 : (bit_shift_left, 3, {}),
				   44 : (bit_shift_left, 3, {'signed' : True}),
				   45 : (bit_shift_left, 3, {'modflags' : False}),
				   46 : (bit_shift_left, 3, {'signed' : True, 'modflags' : False}),
				   47 : (bit_shift_right, 3, {}),
				   48 : (bit_shift_right, 3, {'signed' : True}),
				   49 : (bit_shift_right, 3, {'modflags' : False}),
				   50 : (bit_shift_right, 3, {'signed' : True, 'modflags' : False}),
				   51 : (exit_if_rax, 0, {}),
				   52 : (move_less, 2, {}),
				   53 : (move_greater, 2, {}),
				   54 : (move_equal, 2, {}),
				   55 : (move_less_equal, 2, {}),
				   56 : (move_greater_equal, 2, {}),
				   57 : (move_not_equal, 2, {}),
				   58 : (pop_remove, 0, {}),
				   59 : (popn_remove, 1, {}),
				   60 : (varn, 2, {}),
				   61 : (offset_get, 3, {}),
				   62 : (add_float, 3, {}),
				   63 : (sub_float, 3, {}),
				   64 : (mul_float, 3, {}),
				   65 : (div_float, 3, {}),
				   66 : (power_float, 3, {}),
				   67 : (cmp_float, 2, {}),
				   68 : (int_to_float, 2, {}),
				   69 : (signed_int_to_float, 2, {}),
				   70 : (float_to_int, 2, {}),
				   71 : (float_to_signed_int, 2, {})}


	def inc_rip(self, val):

		"""Increments the RIP register by val."""

		self.registers['RIP'].data[4 : 8] = int.to_bytes(int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') + val, 4, byteorder='little')

	def get_current_code_bytes(self, num):

		"""Gets the current code pointed from by the RIP register."""

		self.cpu.update_from_computer()
		self.processmemory = self.cpu.memory.memorypartitions[self.pname]
		return self.processmemory.get_bytes(int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little'), num)

	def handle_output(self, output):

		"""Handle an output."""

		if output is None:
			return

		if output[0] != 0:
			# Process memory 0 is exit code
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(int.to_bytes(output[0], 2, byteorder='little'), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([2]))))
			# Exit
			raise Exit(output[1])
		else:
			return output[1]

	def parse_argument(self):

		"""Parse the next argument in the code."""

		arg_type = int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')
		self.inc_rip(1)

		if arg_type == 0:   # Register
			# Get register suffix
			reg_suf = list(self.registers.keys())[int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')][1 : ]
			self.inc_rip(1)

			# Get register start
			reg_start_arg = self.handle_output(self.parse_argument())
			reg_start = self.handle_output(self.get(reg_start_arg))

			# Get register length
			reg_len_arg = self.handle_output(self.parse_argument())
			reg_len = self.handle_output(self.get(reg_len_arg))

			return (0, ('reg', (reg_suf, reg_start, reg_len)))
		elif arg_type == 1:  # Memory
			# Get offset
			mem_start_arg = self.handle_output(self.parse_argument())
			mem_start = self.handle_output(self.get(mem_start_arg))

			# Get length
			mem_len_arg = self.handle_output(self.parse_argument())
			mem_len = self.handle_output(self.get(mem_len_arg))

			return (0, ('mem', (mem_start, mem_len)))
		elif arg_type == 2:  # Intermediate value
			# Get length
			int_len = int.from_bytes(self.handle_output(self.get_current_code_bytes(2)), byteorder='little')
			self.inc_rip(2)

			# Get data
			int_data = self.handle_output(self.get_current_code_bytes(int_len))
			self.inc_rip(int_len)

			return (0, ('const', (int_data,)))
		elif arg_type == 3:  # Heap data
			# Get ID
			heap_id = self.handle_output(self.get(self.handle_output(self.parse_argument())))
			
			# Get offset
			heap_offset = self.handle_output(self.get(self.handle_output(self.parse_argument())))
			
			# Get length
			heap_length = self.handle_output(self.get(self.handle_output(self.parse_argument())))

			return (0, ('heap', (heap_id, heap_offset, heap_length)))
		elif arg_type == 4:  # Peripheral data
			# Get ID
			perp_id = self.handle_output(self.get(self.handle_output(self.parse_argument())))
			
			# Get offset
			perp_offset = self.handle_output(self.get(self.handle_output(self.parse_argument())))
			
			# Get length
			perp_length = self.handle_output(self.get(self.handle_output(self.parse_argument())))

			return (0, ('perp', (perp_id, perp_offset, perp_length)))
		elif arg_type == 5:  # Lower shorthand register
			# Get register suffix
			reg_suf = list(self.registers.keys())[int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')][1 : ]
			self.inc_rip(1)

			return (0, ('reg', (reg_suf, b'\x00', b'\x04')))
		elif arg_type == 6:  # Upper shorthand register
			# Get register suffix
			reg_suf = list(self.registers.keys())[int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')][1 : ]
			self.inc_rip(1)

			return (0, ('reg', (reg_suf, b'\x04', b'\x04')))
		elif arg_type == 7:  # Process memory
			# Get PID
			mem_pid_arg = self.handle_output(self.parse_argument())
			mem_pid = self.handle_output(self.get(mem_start_arg))

			# Get offset
			mem_start_arg = self.handle_output(self.parse_argument())
			mem_start = self.handle_output(self.get(mem_start_arg))

			# Get length
			mem_len_arg = self.handle_output(self.parse_argument())
			mem_len = self.handle_output(self.get(mem_len_arg))

			return (0, ('pmem', (mem_pid, mem_start, mem_len)))
		else:
			return (14, "Not a supported data type.")

	def _execute(self):

		"""Begin execution of the data in the core's designated process memory."""

		while int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') < int.from_bytes(self.registers['RDS'].data[4 : 8], byteorder='little') and self.running and not self.error:
			# Get opcode
			opcode = int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')
			self.inc_rip(1)
			if not opcode in self.opcode_dict:
				self.handle_output((29, "Invalid opcode."))
			func, n_args, d_args = self.opcode_dict[opcode]
			# Get args
			args = []
			for arg in range(n_args):
				args.append(self.handle_output(self.parse_argument()))
			# Run the opcode
			try:
				self.handle_output(func(*([self] + args), **d_args))
			except Interrupt as e:
				self.running = False
				return

		if not self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].waiting and self.running:
			# Exitcode 0
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0, 0]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([2]))))
			self.output_exit = (0, None)
			self.running = False

	def _execute_num(self, num):

		"""Execute the next num commands.
		   Args: num -> number of commands to run"""

		if hasattr(self, 'output_exit'):
			return 

		num_executed = 0

		while int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') < int.from_bytes(self.registers['RDS'].data[4 : 8], byteorder='little') and self.running and not self.error and num_executed < num:
			# Get opcode
			opcode = int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')
			self.inc_rip(1)
			if not opcode in self.opcode_dict:
				self.handle_output((29, "Invalid opcode."))
			func, n_args, d_args = self.opcode_dict[opcode]
			# Get args
			args = []
			for arg in range(n_args):
				args.append(self.handle_output(self.parse_argument()))
			# Run the opcode
			try:
				self.handle_output(func(*([self] + args), **d_args))
			except Interrupt as e:
				# Catch interrupts
				return

			num_executed += 1

		if int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') >= int.from_bytes(self.registers['RDS'].data[4 : 8], byteorder='little') and not self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].waiting and self.running:
			# We have got to the end of the code
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0, 0]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([2]))))
			self.output_exit = (0, None)

	def execute(self):

		"""Begin execution of the data in the core's designated process memory."""

		if not hasattr(self, 'processmemory'):
			# Not initialized
			self.output_exit = (0xfe, "Not initialized.")
			self.error = True
			self.running = False
			return self.output_exit

		self.running = True

		try:
			try:
				self._execute()
			except Exit as e:
				# Catch exits
				self.cpu.update_from_computer()
				self.processmemory = self.cpu.memory.memorypartitions[self.pname]
				self.output_exit = (int.from_bytes(self.processmemory.get_bytes(self.processmemory.es - 2, 2)[1], byteorder='little'), str(e))
				self.running = False
				self.error = True
		except Exception as e:
			# Catch internal errors
			import traceback
			traceback.print_exc()
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0xff, 0x0]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([2]))))
			self.output_exit = (0xff, str(e))
			self.running = False
			self.error = True

		if hasattr(self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid], 'output'):
			self.output_exit = self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].output

		self.running = False
		
		return self.output_exit

	def execute_num(self, num):

		"""Execute the next num commands.
		   Args: num -> number of commands to run"""

		if not hasattr(self, 'processmemory'):
			# Not initialized
			self.output_exit = (0xfe, "Not initialized.")
			self.error = True
			self.running = False
			return self.output_exit

		self.running = True

		try:
			try:
				self._execute_num(num)
			except Exit as e:
				# Catch exits
				self.cpu.update_from_computer()
				self.processmemory = self.cpu.memory.memorypartitions[self.pname]
				self.output_exit = (int.from_bytes(self.processmemory.get_bytes(self.processmemory.es - 2, 2)[1], byteorder='little'), str(e))
				self.error = True
		except Exception as e:
			# Catch internal errors
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0xff, 0x0]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([2]))))
			self.output_exit = (0xff, str(e))
			self.error = True

		if hasattr(self, 'output_exit'):
			self.running = False
			return self.output_exit

		self.running = False
		
		return

	def unload(self):

		"""Unload the process from the CPU."""

		del self.processmemory
		del self.registers
		del self.error
		del self.running
		del self.pname
		del self.tid
		if hasattr(self, 'output_exit'):
			del self.output_exit

	def __repr__(self):

		"""Get the string representation of the CPU Core."""

		if hasattr(self, 'processmemory'):
			return "<CPUCore initialized>"
		else:
			return "<CPUCore>"

	def __str__(self):

		"""Get the string representation of the CPU Core."""

		return self.__repr__()


class ALU:

	"""The arithmetic logic unit for a CPU."""

	def __init__(self):

		"""Create the ALU."""

		pass

	def add(self, a, b, answer_length):

		"""Add a and b as integers.
		   Args: a -> bytearray as the first piece of data to add.
		   		 b -> bytearray as the second piece of data to add.
		   		 answer_length -> length of the answer"""

		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')

		try:
			answer = int.to_bytes(a_int + b_int, answer_length, byteorder='little')
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def sub(self, a, b, answer_length):
		
		"""Subtract a and b as integers.
		   Args: a -> bytearray as the first piece of data to subtract.
		   		 b -> bytearray as the second piece of data to subtract.
		   		 answer_length -> length of the answer"""
		
		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int - b_int, answer_length, byteorder='little', signed=True)
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, answer)

	def mul(self, a, b, answer_length):

		"""Multiply a and b as unsigned integers.
		   Args: a -> bytearray as the first piece of data to multiply.
		   		 b -> bytearray as the second piece of data to multiply.
		   		 answer_length -> length of the answer"""
		
		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int * b_int, answer_length, byteorder='little')
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, answer)

	def mul_signed(self, a, b, answer_length):

		"""Multiply a and b as signed integers.
		   Args: a -> bytearray as the first piece of data to multiply.
		   		 b -> bytearray as the second piece of data to multiply.
		   		 answer_length -> length of the answer"""
		
		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little', signed=True)
		b_int = int.from_bytes(b, byteorder='little', signed=True)
		answer_length = int.from_bytes(answer_length, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int * b_int, answer_length, byteorder='little', signed=True)
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, answer)

	def div(self, a, b, answer_length0, answer_length1):

		"""Divide a and b as unsigned integers.
		   Args: a -> bytearray as the first piece of data to divide.
		   		 b -> bytearray as the second piece of data to divide.
		   		 answer_length0 -> length of the answer
		   		 answer_length1 -> length of the modulus"""
		
		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		b_int = int.from_bytes(b, byteorder='little')
		answer_length0 = int.from_bytes(answer_length0, byteorder='little')
		answer_length1 = int.from_bytes(answer_length1, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int // b_int, answer_length0, byteorder='little')
			modulus = int.to_bytes(a_int % b_int, answer_length1, byteorder='little')
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, (answer, modulus))

	def div_signed(self, a, b, answer_length0, answer_length1):

		"""Divide a and b as signed integers.
		   Args: a -> bytearray as the first piece of data to divide.
		   		 b -> bytearray as the second piece of data to divide.
		   		 answer_length0 -> length of the answer
		   		 answer_length1 -> length of the modulus"""
		
		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little', signed=True)
		b_int = int.from_bytes(b, byteorder='little', signed=True)
		answer_length0 = int.from_bytes(answer_length0, byteorder='little')
		answer_length1 = int.from_bytes(answer_length1, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int // b_int, answer_length0, byteorder='little', signed=True)
			modulus = int.to_bytes(a_int % b_int, answer_length1, byteorder='little', signed=True)
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, (answer, modulus))

	def bit_and(self, a, b, answer_length):

		"""Preform an and gate on a and b.
		   Args: a -> bytearray as the first piece of data to AND.
		   		 b -> bytearray as the second piece of data to AND.
		   		 answer_length -> length of the answer"""
		
		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int & b_int, answer_length, byteorder='little')
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, answer)

	def bit_or(self, a, b, answer_length):

		"""Preform an or gate on a and b.
		   Args: a -> bytearray as the first piece of data to OR.
		   		 b -> bytearray as the second piece of data to OR.
		   		 answer_length -> length of the answer"""

		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int | b_int, answer_length, byteorder='little')
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, answer)

	def bit_xor(self, a, b, answer_length):

		"""Preform an xor gate on a and b.
		   Args: a -> bytearray as the first piece of data to XOR.
		   		 b -> bytearray as the second piece of data to XOR.
		   		 answer_length -> length of the answer"""

		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')
		
		try:
			answer = int.to_bytes(a_int ^ b_int, answer_length, byteorder='little')
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, answer)

	def bit_not(self, a, b, answer_length):

		"""Preform a not gate on a.
		   Args: a -> bytearray as the data to NOT.
		   		 answer_length -> length of the answer"""

		# Convert bytes into bits
		a_int = int.from_bytes(a, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')
		
		try:
			answer = int.to_bytes((2 ** (8 * len(a)) - 1) - a_int, answer_length, byteorder='little')
		except OverflowError as e:
			return (18, "Answer overflow.")
			
		return (0, answer)

	def bit_shift_left(self, a, b, answer_length, signed=False):

		"""Preform a bit shift left on a and b.
		   Args: a -> bytearray as the data to shift
		         b -> bytearray as the amount of bits to shift
		         answer_length -> length of the answer
		         signed -> whether to use a signed bit shift"""

		# Convert bytes to bits
		a_int = int.from_bytes(a, byteorder='little', signed=signed)
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')

		try:
			answer = int.to_bytes(a_int << b_int, answer_length, byteorder='little', signed=signed)
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def bit_shift_right(self, a, b, answer_length, signed=False):

		"""Preform a bit shift right on a and b.
		   Args: a -> bytearray as the data to shift
		         b -> bytearray as the amount of bits to shift
		         answer_length -> length of the answer
		         signed -> whether to use a signed bit shift"""

		# Convert bytes to bits
		a_int = int.from_bytes(a, byteorder='little', signed=signed)
		b_int = int.from_bytes(b, byteorder='little')
		answer_length = int.from_bytes(answer_length, byteorder='little')

		try:
			answer = int.to_bytes(a_int >> b_int, answer_length, byteorder='little', signed=signed)
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def __repr__(self):

		"""Get the string representation of the ALU."""

		return "<ALU>"

	def __str__(self):

		"""Get the string representation of the ALU."""

		return self.__repr__()


class FPU:

	"""The floating point logic unit for a CPU."""

	def __init__(self):

		"""Create the FPU."""

		pass

	def add(self, a, b):

		"""Add a and b as floats.
		   Args: a -> bytearray as the first piece of data to add.
		   		 b -> bytearray as the second piece of data to add."""

		# Convert bytes into bits
		a_float = struct.unpack('f', a)[0]
		b_float = struct.unpack('f', b)[0]

		try:
			answer = struct.pack('f', a_float + b_float)
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def sub(self, a, b):

		"""subtract a and b as floats.
		   Args: a -> bytearray as the first piece of data to subtract.
		   		 b -> bytearray as the second piece of data to subtract."""

		# Convert bytes into bits
		a_float = struct.unpack('f', a)[0]
		b_float = struct.unpack('f', b)[0]

		try:
			answer = struct.pack('f', a_float - b_float)
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def mul(self, a, b):

		"""Multiply a and b as floats.
		   Args: a -> bytearray as the first piece of data to multiply.
		   		 b -> bytearray as the second piece of data to multiply."""

		# Convert bytes into bits
		a_float = struct.unpack('f', a)[0]
		b_float = struct.unpack('f', b)[0]

		try:
			answer = struct.pack('f', a_float * b_float)
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def div(self, a, b):

		"""Divide a and b as floats.
		   Args: a -> bytearray as the first piece of data to divide.
		   		 b -> bytearray as the second piece of data to divide."""

		# Convert bytes into bits
		a_float = struct.unpack('f', a)[0]
		b_float = struct.unpack('f', b)[0]

		try:
			answer = struct.pack('f', a_float / b_float)
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def power(self, a, b):

		"""Raise a to the power of b as floats.
		   Args: a -> bytearray as the first piece of data to raise.
		   		 b -> bytearray as the second piece of data to raise."""

		# Convert bytes into bits
		a_float = struct.unpack('f', a)[0]
		b_float = struct.unpack('f', b)[0]

		try:
			answer = struct.pack('f', a_float ** b_float)
		except OverflowError as e:
			return (18, "Answer overflow.")

		return (0, answer)

	def __repr__(self):

		"""Get the string representation of the FPU."""

		return "<FPU>"

	def __str__(self):

		"""Get the string representation of the FPU."""

		return self.__repr__()


class CPU:

	"""The main CPU object."""

	def __init__(self, computer, memory):

		"""Create the CPU."""

		self.memory = memory
		self.computer = computer

		self.cores = []

	def add_core(self, core):

		"""Add a core to the CPU.
		   Args: core -> the core to add"""

		self.cores.append(core)
		return len(self.cores) - 1

	def init_core(self, cid, processmemory, pname, tid):

		"""Initialize a core.
		   Args: cid -> the id/index of the core to initialize
		         processmemory -> the process memory to initialize the core with
		         pname -> the process name the process memory is designated in the CPU memory
		         tid -> the thread id"""

		self.cores[cid].initialize(processmemory, pname, tid)

	def begin_execute_core(self, cid):

		"""Execute the code on core cid.
		   Args: cid -> the core id/index"""

		thread = threading.Thread(target=self.cores[cid].execute)
		thread.start()

	def begin_execute_core_num(self, cid, num):

		"""Execute num commands on core cid.
		   Args: cid -> the core id/index
		   		 num -> the number of commands to run"""

		thread = threading.Thread(target=self.cores[cid].execute_num, args=(num,))
		thread.start()

	def await_execution(self, cid):

		"""Await execution to finish for core cid.
		   Args: cid -> the core id/index"""

		# Wait until the core has finished
		while hasattr(self.cores[cid], 'running') and self.cores[cid].running:
			pass

	def get_return(self, cid):

		"""Get the return value of core cid.
		   Args: cid -> the core is/index"""

		return self.cores[cid].output_exit

	def unload_core(self, cid):

		"""Unload core cid
		   Args: cid -> the core id/index"""

		self.cores[cid].unload()

	def update_memory(self, memory):

		"""Update the memory in the computer. Called by the individual CPU cores.
		   Args: memory -> new memory to update"""
		
		self.memory = memory
		self.computer.memory = self.memory

	def update_from_computer(self):

		"""Update this memory from the computer."""

		self.memory = self.computer.memory

	def __repr__(self):

		"""Get the string representation of the CPU."""

		return "<CPU with " + str(len(self.cores)) + " cores>"

	def __str__(self):

		"""Get the string representation of the CPU."""

		return self.__repr__()
