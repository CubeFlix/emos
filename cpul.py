"""64 Bit CPU and computer emulation in Python.
Written by Kevin Chen."""


# Imports
import time
import threading
import copy


# Constants
MAXPROCESSMEMORY = int(2 ** 32 / 4) - 1
MAXMEMORY = 2 ** 32 - 1
ENCODING = 'utf-8'


class Exit(Exception):

	"""Exit exception. This is to be raised when an error occurs."""

	pass


class Interrupt(Exception):

	"""Interrupt exception. This is to be raised when a system interrupt is called."""

	pass


def getsize(datadescriptor):

	"""Get the size of a data descriptor tuple."""

	if datadescriptor[0] == 'reg':
		size = datadescriptor[1][2]
	elif datadescriptor[0] == 'mem':
		size = datadescriptor[1][1]
	elif datadescriptor[0] == 'heap':
		raise NotImplementedError("Heap is not implemented yet.")
	elif datadescriptor[0] == 'ram':
		raise NotImplementedError("RAM is not implemented yet.")
	elif datadescriptor[0] == 'perp':
		raise NotImplementedError("Peripheral memory is not implemented yet.")
	elif datadescriptor[0] == 'pmem':
		raise NotImplementedError("Other process memory is not implemented yet.")
	else:
		return (15, "Not a supported destination type.")	

	return (0, size)


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


class MemorySection:

	"""A memory section class. Usually managed by the CPU and OS."""

	def __init__(self, name, size, data):

		"""Create a memory section.
		   Args: name -> the name of the memory section
		   		 size -> the size of the memory section
		   	     data -> the data to initialize the section with"""

		self.name = name
		self.size = size
		self.data = bytearray(data)

	def set_data(self, data):

		"""Set the data."""

		self.data = bytearray(data)
		self.size = len(data)
		return (0, None)

	def pop(self):

		"""Pop off 4 bytes from the memory."""

		if self.size < 4:
			# Size is less than 4
			return (3, "Stack is not large enough.")
		data = self.data[0 : 4]
		del self.data[0 : 4]
		self.size -= 4
		return (0, data)

	def push(self, data):

		"""Push bytes onto the memory."""

		self.data = data + self.data
		self.size += len(data)
		return (0, None)

	def popn(self, n):

		"""Pop n bytes from the memory.
		   Args: n -> number of bytes to pop"""

		if self.size < n:
			# Size is less than n
			return (3, "Stack is not large enough.")
		data = self.data[0 : n]
		del self.data[0 : n]
		self.size -= n
		return (0, data)

	def removebytes(self, numbytes):

		"""Remove numbytes bytes from the end of the memory."""

		if self.size < numbytes:
			return (4, "Not enough memory to remove.")
		self.data = self.data[ : self.size - numbytes]
		self.size -= numbytes
		return (0, None)

	def __repr__(self):

		"""Get the string representation of the memory."""

		return "<MemorySection " + self.name + ">"

	def __str__(self):

		"""Get the string representation of the memory."""

		return self.__repr__()


class ProcessMemory:

	"""Memory set for a process. Similar to virtual memory, as all data pointers will be continuous. Managed by the CPU and the OS."""

	def __init__(self, code, data, stack, maxsize=MAXPROCESSMEMORY):

		"""Create a chunk of memory for a process.
		   Args: code -> code section
		   		 data -> data section
		   		 stack -> stack section
		   		 maxsize -> maximum process memory"""

		self.code = MemorySection('code', len(code), code)
		self.data = MemorySection('data', len(data), data)
		self.stack = MemorySection('stack', len(stack), stack)
		self.cs = 0
		self.ds = len(self.code.data)
		self.ss = self.ds + len(self.data.data)
		self.es = self.ss + len(self.stack.data)
		self.maxsize = maxsize

	def get_byte(self, offset):

		"""Get byte from the memory.
		   Args: offset -> offset the byte is located at"""

		# Calculate the section the offset is in
		if offset - self.ds < 0:
			# Code section
			return (0, self.code.data[offset])
		elif offset - self.ss < 0:
			# Data section
			return (0, self.data.data[offset - self.ds])
		elif offset - self.es < 0:
			# Stack section
			return (0, self.stack.data[offset - self.ss])
		elif offset >= self.es:
			return (5, "Offset is not in memory.")

	def get_bytes(self, offset, numbytes):

		"""Get bytes from the memory.
		   Args: offset -> offset to start at
		   		 numbytes -> number of bytes to get"""

		data = bytearray(numbytes)

		for i in range(offset, offset + numbytes):
			exitcode, currentbyte = self.get_byte(i)
			if exitcode != 0:
				return (exitcode, currentbyte)
			data[i - offset] = currentbyte
		return (0, data)

	def set_byte(self, data, offset):

		"""Set the byte at offset offset to data data.
		   Args: data -> data
		   		 offset -> offset"""

		if (offset > self.es) and (offset >= self.maxsize):
			return (6, "Not enough memory.")
		# Calculate the section the offset is in
		if offset - self.ds < 0:
			# Code section
			return (7, "Cannot write to code section.")
		elif offset - self.ss < 0:
			# Data section
			self.data.data[offset - self.ds] = bytearray(data)[0]
			return (0, None)
		elif offset - self.es < 0:
			# Stack section
			self.stack.data[offset - self.ss] = bytearray(data)[0]
			return (0, None)
		else:
			# Not in range
			to_add = bytearray(offset - self.es) + bytearray(data)
			self.es += len(to_add)
			return self.stack.set_data(self.stack.data + to_add)
			
	def set_bytes(self, data, offset):

		"""Set bytes to the memory.
		   Args: data -> data to add
		   		 offset -> offset to start at"""

		for i in range(len(data)):
			exitcode, message = self.set_byte(bytearray([data[i]]), offset + i)
			if exitcode != 0:
				return (exitcode, message)

		return (0, None)

	def pop_stack(self):

		"""Pop 4 bytes from the stack."""

		self.es -= 4
		result = self.stack.pop()
		if result[0] != 0:
			self.es += 4
			return result
		return result

	def popn_stack(self, n):

		"""Pop n bytes from the stack.
		   Args: n -> number of bytes to pop"""

		self.es -= n
		result = self.stack.popn(n)
		if result[0] != 0:
			self.es += n
			return result
		return result

	def push_stack(self, data):

		"""Push 4 bytes to the stack.
		   Args: data -> data to push"""

		if self.es + 4 >= self.maxsize:
			return (8, "Not enough memory to push.")
		self.es += 4
		return self.stack.push(data)

	def pushn_stack(self, data):

		"""Push data bytes to the stack.
		   Args: data -> data to push"""

		if self.es + len(data) >= self.maxsize:
			return (8, "Not enough memory to push.")
		self.es += len(data)
		return self.stack.push(data)

	def removebytes_stack(self, numbytes):

		"""Remove numbytes bytes from the end of the stack.
		   Args: numbytes -> number of bytes to remove"""

		exitcode, msg = self.stack.removebytes(numbytes)
		if exitcode == 0:
			self.es -= numbytes
			return (0, None)
		else:
			return (exitcode, msg)

	def __repr__(self):

		"""Get the string representation of the memory."""

		return "<ProcessMemory size " + hex(self.es) + ">"

	def __str__(self):

		"""Get the string representation of the memory."""

		return self.__repr__()


class Memory:

	"""The main memory/RAM for a computer."""

	def __init__(self, maxsize=MAXMEMORY):

		"""Create the memory module.
		   Args: maxsize -> maximum size of the memory"""

		self.maxsize = maxsize
		self.memorypartitions = {}
		self.size = 0

	def add_memory_partition(self, name, memorypartition):

		"""Add a memory partition to the memory.
		   Args: name -> name of the partition
		   		 memorypartition -> the memory partition to add. can be a MemorySection (usually heap managed by the OS), or ProcessMemory (thread-specific)"""

		self.memorypartitions[name] = memorypartition
		self.recalculate_length()
		if self.size > self.maxsize:
			self.delete_process(name)
			return (11, "Not enough memory.")
		return (0, None)

	def delete_memory_partition(self, name):

		"""Delete a memory partition.
		   Args: name -> name to remove"""
		
		if not name in self.memorypartitions:
			return (12, "Name not in memory.")

		del self.memorypartitions[name]
		self.recalculate_length()
		return (0, None)

	def edit_memory_partition(self, name, memorypartition):

		"""Edit a memory partition.
		   Args: name -> the name of the partition
		         memorypartition -> the data in the partition"""

		if not name in self.memorypartitions:
			return (12, "Name not in memory.")

		self.memorypartitions[name] = memorypartition
		self.recalculate_length()

		if self.size > self.maxsize:
			return (11, "Not enough memory.")

		return (0, None)

	def recalculate_length(self):

		"""Recalculate the size of the memory."""

		size = 0
		for name, memorypartition in self.memorypartitions.items():
			if type(memorypartition) == MemorySection:
				# Memory section, so use size
				size += memorypartition.size
			elif type(memorypartition) == ProcessMemory:
				# Process memory, so use es
				size += memorypartition.es

		self.size = size
		return (0, self.size)

	def get_byte(self, offset):

		"""Get a single byte from memory at offset offset.
		   Args: offset -> the offset to get the byte from"""

		currentBase

	def __repr__(self):

		"""Get the string representation of the memory."""

		return "<Memory size " + hex(self.size) + " with " + str(len(self.memorypartitions)) + " partition(s)>"

	def __str__(self):

		"""Get the string representation of the memory."""

		return self.__repr__()


class CPUCore:

	"""The main 64 bit CPU core class."""
	
	def __init__(self, cpu, speed=None):

		"""Create the CPU core.
		   Args: cpu -> the CPU the core is attached to
		   		 speed -> the speed in Hertz or none"""

		self.cpu = cpu
		self.alu = ALU()
		self.speed = speed

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
		elif desttype == 'heap':
			# Heap memory destination
			memId = int.from_bytes(dest[1][0], byteorder='little')
			memOffset = int.from_bytes(dest[1][1], byteorder='little')
			memSize = int.from_bytes(dest[1][2], byteorder='little')
			return self.cpu.computer.operatingsystem.get_memory(memId, memOffset, memSize)
		elif srctype == 'ram':
			# RAM source
			# update cpu memory
			raise NotImplementedError("RAM is not implemented yet.")
		elif srctype == 'perp':
			# Peripheral memory source
			memId = int.from_bytes(dest[1][0], byteorder='little')
			memOffset = int.from_bytes(dest[1][1], byteorder='little')
			memSize = int.from_bytes(dest[1][2], byteorder='little')

			if not ('perp', memId) in self.cpu.computer.memory.memorypartitions:
				return (23, "Memory ID is not in the computer memory.")

			memPart = self.cpu.computer.memory.memorypartitions[('perp', memId)]

			if memOffset + memSize > memPart.size or memSize != len(srcdata):
				return (17, "Memory out of range.")

			newData = memPart.data[memOffset : memOffset + memSize]

			return (0, newData)
		elif srctype == 'pmem':
			# Get a different processes memory
			memId = int.from_bytes(dest[1][0], byteorder='little')
			memOffset = int.from_bytes(dest[1][1], byteorder='little')
			memSize = int.from_bytes(dest[1][2], byteorder='little')

			if destlength != len(srcdata) or self.cpu.computer.memory.memorypartitions[('proc', memId)].ss < memOffset:
				return (17, "Memory section is not large enough to hold given data.")

			if not ('proc', memId) in self.cpu.computer.memory.memorypartitions:
				return (23, "Memory ID is not in the computer memory.")

			destexitcode, msg = self.cpu.computer.memory.memorypartitions[('proc', memId)].get_bytes(srcdata, destoffset)
			if destexitcode != 0:
				return (destexitcode, msg)
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
		elif desttype == 'ram':
			# Move to RAM
			# updates cpu memory
			raise NotImplementedError("RAM is not implemented yet.")
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

		if self.registers['RFLAGS'].data[7] == 1 or lf.registers['RFLAGS'].data[5] == 1:
			return self.jmp(addr)
		return (0, None)

	def jmp_greater_equal(self, addr):

		"""Jump to addr if the equal or greater than flag is on.
		   Args: addr -> the address to jump to if the equal or greater than flag is on"""

		if self.registers['RFLAGS'].data[7] == 1 or lf.registers['RFLAGS'].data[6] == 1:
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

		output = self.handle_output(self.get(output))[0]

		self.running = False
		self.output_exit = (output, None)

		if int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') >= int.from_bytes(self.registers['RDS'].data[4 : 8], byteorder='little'):
			pass
		else:
			# Add the exitcode
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([output]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([1]))))

		return (output, None)

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

		n = self.handle_output(self.get(n))
		exitcode, data = self.processmemory.popn_stack()
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
				   40 : (interrupt, 1, {})}


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
			self.running = False
			self.error = True
			# Process memory 0 is exit code
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([output[0]]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([1]))))
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
			int_len = int.from_bytes(self.handle_output(self.get_current_code_bytes(4)), byteorder='little')
			self.inc_rip(4)

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
		else:
			return (14, "Not a supported data type.")

	def _execute(self):

		"""Begin execution of the data in the core's designated process memory."""

		self.running = True

		while int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') < int.from_bytes(self.registers['RDS'].data[4 : 8], byteorder='little') and self.running and not self.error:
			# Get opcode
			opcode = int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')
			self.inc_rip(1)
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
			if self.speed:
				time.sleep(1 / self.speed)

		if not self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].waiting:
			# Exitcode 0
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([1]))))
			self.output_exit = (0, None)
			self.running = False

	def _execute_num(self, num):

		"""Execute the next num commands.
		   Args: num -> number of commands to run"""

		if hasattr(self, 'output_exit'):
			return 

		self.running = True
		num_executed = 0

		while int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') < int.from_bytes(self.registers['RDS'].data[4 : 8], byteorder='little') and self.running and not self.error and num_executed < num:
			# Get opcode
			opcode = int.from_bytes(self.handle_output(self.get_current_code_bytes(1)), byteorder='little')
			self.inc_rip(1)
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
				self.running = False
				return
			if self.speed:
				time.sleep(1 / self.speed)

			num_executed += 1

		if int.from_bytes(self.registers['RIP'].data[4 : 8], byteorder='little') >= int.from_bytes(self.registers['RDS'].data[4 : 8], byteorder='little') and not self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].waiting:
			# We have got to the end of the code
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([1]))))
			self.output_exit = (0, None)

		self.running = False

	def execute(self):

		"""Begin execution of the data in the core's designated process memory."""

		if not hasattr(self, 'processmemory'):
			# Not initialized
			self.output_exit = (0xfe, "Not initialized.")
			self.error = True
			self.running = False
			return self.output_exit

		try:
			try:
				self._execute()
			except Exit as e:
				# Catch exits
				self.cpu.update_from_computer()
				self.processmemory = self.cpu.memory.memorypartitions[self.pname]
				self.output_exit = (self.processmemory.get_bytes(self.processmemory.es, self.processmemory.es + 1)[0], str(e))
		except Exception as e:
			# Catch internal errors
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0xff]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([1]))))
			self.output_exit = (0xff, str(e))
			self.running = False
			self.error = True

		if hasattr(self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid], 'output'):
			self.output_exit = self.cpu.computer.operatingsystem.processes[self.pname[1]].threads[self.tid].output
		
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
				self.output_exit = (self.processmemory.get_bytes(self.processmemory.es, self.processmemory.es + 1)[0], str(e))
		except Exception as e:
			# Catch internal errors
			# Temp
			import traceback
			traceback.print_exc()
			self.cpu.update_from_computer()
			self.processmemory = self.cpu.memory.memorypartitions[self.pname]
			self.set(bytes([0xff]), ("MEM", (int.to_bytes(self.processmemory.es, 4, byteorder='little'), bytes([1]))))
			self.output_exit = (0xff, str(e))
			self.running = False
			self.error = True
		
		if hasattr(self, 'output_exit'):
			return self.output_exit

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

	"""The ALU for a CPU."""

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

	def __repr__(self):

		"""Get the string representation of the ALU."""

		return "<ALU>"

	def __str__(self):

		"""Get the string representation of the ALU."""

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


class HardDrive:

	"""A hard drive managed by the OS."""

	def __init__(self, computer, outfile):

		"""Create the hard drive.
		   Args: computer -> the computer the hard drive is attached to
		         outfile -> the name of the output file/virtual hard disk"""

		self.computer = computer
		self.outfile = outfile
		self.metadata = bytearray()
		self.blocks = []

	def _backend_update(self):

		"""Update the virtual hard drive file."""

		f = open(self.outfile, 'wb')
		f.write(self.get_full_buffer())
		f.close()


class Computer:

	"""The main computer object."""

	def __init__(self):

		"""Create the computer."""

		self.peripherals = {}
		self.peripheral_ids = []

	def set_memory(self, memory):

		"""Set the memory for the computer.
		   Args: memory -> the memory to set"""

		self.memory = memory

	def set_cpu(self, cpu):

		"""Set the CPU for the computer.
		   Args: cpu -> the CPU to set"""

		self.cpu = cpu

	def set_os(self, os):

		"""Set the operating system for the computer.
		   Args: os -> the operating system to set"""

		self.operatingsystem = os

	def start(self):

		"""Start up the computer."""

		# self.bootload()

	def add_peripheral(self, peripheral):

		"""Add a peripheral to the computer.
		   Args: peripheral -> the peripheral to add"""

		# Find a valid peripheral ID
		for i in range(max(self.peripheral_ids) if self.peripheral_ids else 0):
			if not i in self.peripheral_ids:
				# This peripheral ID is free
				current_pid = i
				break

		# No holes, so add a new PID
		current_pid = (max(self.peripheral_ids) if self.peripheral_ids else -1) + 1

		# Add the peripheral
		self.peripheral_ids.append(current_pid)
		self.peripherals[current_pid] = peripheral

		return current_pid

	def remove_peripheral(self, pid):

		"""Remove a peripheral from the computer.
		   Args: pid -> peripheral ID to remove"""

		self.peripheral_ids.remove(pid)
		del self.peripherals[pid]

	def interrupt(self, iid, pid, tid):

		"""Call an interrupt.
		   Args: iid -> interrupt ID to call
		         pid -> process ID
		         tid -> thread ID"""

		iid = int.from_bytes(iid, byteorder='little')

		for peripheral_id, peripheral in self.peripherals.items():
			# Check if the peripheral supports the interrupt ID
			if iid in peripheral.defined_interrupts:
				# Call the interrupt
				return peripheral.handle(iid, pid, tid)

		return (22, "Not a supported interrupt.")

	def __repr__(self):

		"""Get the string representation of the computer."""

		return "<Computer>"

	def __str__(self):

		"""Get the string representation of the computer."""

		return self.__repr__()


class OperatingSystem:

	"""The main operating system or OS the computer uses. System calls through interrupts can allow for memory and process management (heap and process memory), along with other things such as IO.
	   The OS also handles files and process management with memory, ensuring that we don't run out. Finally, the OS can also switch into user mode, letting the user control everything."""

	def __init__(self, computer):

		"""Create the operating system.
		   Args: computer -> the computer the operating system is installed on"""

		self.computer = computer

		self.mem_alloc_ids = []

		self.process_ids = []
		self.processes = {}

		self.running = False

		# Maximum number of operations to run on each thread if no IO is involved
		self.max_operations_per_thread = 100

	def set_max_thread_operations(self, max_operations_per_thread):

		"""Set the maximum number of operations each thread gets to run per iteration, if no IO is involved.
		   Args: max_operations_per_thread -> maximum operations per thread per iteration."""

		self.max_operations_per_thread = max_operations_per_thread

	def allocate_memory(self):

		"""Allocate memory, returning the memory id."""

		for i in range(max(self.mem_alloc_ids) if self.mem_alloc_ids else 0):
			if not i in self.mem_alloc_ids:
				# This id is free
				current_mem_id = i
				break
		# No holes, so add a new id
		current_mem_id = (max(self.mem_alloc_ids) if self.mem_alloc_ids else -1) + 1

		self.computer.memory.add_memory_partition(MemorySection(('mem', current_mem_id), 0, bytearray()))
		self.mem_alloc_ids.append(current_mem_id)
		return (0, current_mem_id)

	def free_memory(self, mem_id):

		"""Free the memory at memory id mem_id.
		   Args: mem_id -> memory id"""

		if not mem_id in self.mem_alloc_ids:
			return (19, "Memory id does not exist.")

		# Free the memory
		self.mem_alloc_ids.remove(mem_id)
		self.computer.memory.delete_memory_partition(('mem', mem_id))

		return (0, None)

	def get_memory_size(self, mem_id):

		"""Get the size of the memory partition mem_id.
		   Args: mem_id -> memory id"""

		if not mem_id in self.mem_alloc_ids:
			return (19, "Memory id does not exist.")

		return (0, self.computer.memory.memorypartitions[('mem', mem_id)].size)

	def get_memory(self, mem_id, start_offset, size):

		"""Get memory mem_id at start_offset with size size.
		   Args: mem_id -> memory id
		   		 start_offset -> starting offset
		   		 size -> amount of memory to get"""

		if not mem_id in self.mem_alloc_ids:
			return (19, "Memory id does not exist.")

		return self.computer.memory.memorypartitions[('mem', mem_id)].get_bytes(start_offset, size)

	def edit_memory(self, mem_id, data, start_offset):

		"""Edit the memory at mem_id, and move data into the memory at start_offset.
		   Args: mem_id -> memory id
		   		 data -> data to edit to
		   		 start_offset -> starting offset"""

		# Get data
		exitcode, current_data = self.get_memory(mem_id, start_offset)
		if exitcode != 0:
			return (exitcode, current_data)

		# Get size
		exitcode, size = self.get_memory_size(mem_id)
		if exitcode != 0:
			return (exitcode, size)

		# Too large, but starts within bounds
		if start_offset + len(data) > size and start_offset < size:
			new_data = current_data[ : start_offset] + data
		# Too large, and starts out of bounds (padding with zero bytes)
		elif start_offset + len(data) > size and start_offset > size:
			new_data = current_data + bytes(start_offset - size) + new_data
		# Within bounds
		else:
			# New data
			new_data = current_data[ : start_offset] + data + current_data[start_offset + len(data) : ]

		return self.computer.memory.edit_memory_partition(('mem', mem_id), new_data)

	def process_create(self, process):

		"""Create a process, returning the PID.
		   Args: process -> the process to use"""

		# Find a valid PID
		for i in range(max(self.process_ids) if self.process_ids else 0):
			if not i in self.process_ids:
				# This PID is free
				current_pid = i
				break
		# No holes, so add a new PID
		current_pid = (max(self.process_ids) if self.process_ids else -1) + 1

		# Add the process
		self.processes[current_pid] = process
		self.process_ids.append(current_pid)

		# Add the process to memory
		self.computer.memory.add_memory_partition(('proc', current_pid), process.processmemory)

		# Update the process
		self.processes[current_pid].state = 'r'
		self.processes[current_pid].pid = current_pid

		return (0, current_pid)

	def thread_create(self, pid, thread):

		"""Create a thread in a process, returning the TID.
		   Args: pid -> the process ID to add to
		         thread -> the thread to use"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		self.processes[pid].threads.append(thread)

		return (0, len(self.processes[pid]))

	def process_terminate(self, pid):

		"""Terminate a process.
		   Args: pid -> the process ID to terminate"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		self.processes[pid].state = 't'

		return (0, None)

	def process_delete(self, pid):

		"""Delete a process.
		   Args: pid -> the process ID to delete."""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		del self.processes[pid].pid
		self.process_ids.remove(pid)
		del self.processes[pid]

		self.computer.memory.delete_memory_partition(('proc', pid))

		return (0, None)

	def thread_terminate(self, pid, tid):

		"""Terminate a process.
		   Args: pid -> the process ID
		         tid -> the thread ID"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		if not tid in self.processes[pid].threads:
			return (21, "TID dosen't exist.")

		self.processes[pid].threads[tid].running = False

		return (0, None)

	def thread_delete(self, pid):

		"""Delete a process.
		   Args: pid -> the process ID to delete."""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		if not tid in self.processes[pid].threads:
			return (21, "TID dosen't exist.")

		del self.processes[pid].threads[tid]

		return (0, None)

	def process_fork(self, pid):

		"""Fork a process.
		   Args: pid -> the process ID to fork"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		return self.process_create(self.processes[pid])

	def thread_fork(self, pid, tid):

		"""Fork a thread.
		   Args: pid -> the process ID
		         tid -> the thread ID to fork"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		if not tid in self.processes[pid].threads:
			return (21, "TID dosen't exist.")

		return self.thread_create(pid, self.processes[pid].threads[tid])

	def thread_await(self, pid, tid):

		"""Wait until a thread is done.
		   Args: pid -> the process ID
		         tid -> the thread ID"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		if not tid in self.processes[pid].threads:
			return (21, "TID dosen't exist.")

		while self.processes[pid].threads[tid].running or self.processes[pid].threads[tid].waiting:
			pass

		return (0, None)

	def process_await(self, pid):

		"""Wait until a process is done.
		   Args: pid -> the process ID"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		while self.processes[pid].state == 'r':
			pass

		return (0, None)

	def update_process_memory_global(self, pid, tid):

		"""Update process PID's process memory in processes from the memory. Updates all running processes CPU memory as well.
		   Args: pid -> process id to update"""

		self.computer.memory.memorypartitions[('proc', pid)].data = self.processes[pid].processmemory.data

		# Update all processes in CPU
		for cid, cpu in enumerate(self.computer.cpu.cores):
			try:
				if cpu.pname == ('proc', pid):
					# Update this CPU core
					self.computer.cpu.cores[cid].processmemory.data = self.processes[pid].processmemory.data
			except:
				pass

	def halt_thread(self, pid, tid, exitcode):

		"""Halt a thread.
		   Args: pid -> process id
		         tid -> thread id to halt"""

		# Terminate the program with exitcode
		self.processes[pid].threads[tid].output = (exitcode, None)
		e_exitcode = self.processes[pid].threads[tid].stack.set_data(self.processes[pid].threads[tid].stack.data + bytes([exitcode]))
		self.processes[pid].threads[tid].running = False
		if not all([self.processes[pid].threads[t].running for t in self.processes[pid].threads]):
			# All threads are done
			self.processes[pid].state = 't'
			self.processes[pid].output = (exitcode, None)
		return e_exitcode

	def systemcall(self, pid, tid):

		"""Preform a system call. NOTE: never uses the stack
		   Args: pid -> process ID of the process that called the system call
		         tid -> thread ID of the thread that called the system call"""

		try:
			self.processes[pid].threads[tid].waiting = True
			# Wait until the CPU has finished the thread (and registers are committed)
			while True:
				ready = True
				for cpu in self.computer.cpu.cores:
					try:
						if cpu.pname == ('proc', pid) and cpu.tid == tid:
							ready = False
					except:
						pass
				if ready:
					break
			# Get the system call ID
			syscallid = int.from_bytes(self.processes[pid].threads[tid].registers['RAX'].get_bytes(0, 4)[1], byteorder='little')
			
			# Run the system call (NOTE: all syscalls must call update_process_memory_global after modifying memory)
			# NOTE: All system calls must modify memory in the processes memory data, not global memory data. Using the method update_process_memory_global, memory can be synced up with all processes. 
			if syscallid == 0:
				# Terminate with exitcode in RBX
				s_exitcode = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				exitcode = self.halt_thread(pid, tid, s_exitcode)
			elif syscallid == 1:
				# Temp: Wait 2 sec
				time.sleep(2)
				exitcode = (0, None)
			elif syscallid == 2:
				# Temp: get one char
				text = bytes(input(), ENCODING)
				self.processes[pid].threads[tid].stack.data = text
				exitcode = (0, None)
			# Update memory in process
			self.update_process_memory_global(pid, tid)
			# In case of errors, set the pidtid to not running/error
			self.processes[pid].threads[tid].waiting = False
			# Check for errors
			if exitcode[0] != 0:
				# Handle exitcode
				self.halt_thread(pid, tid, exitcode[0])
		except Exception as e:
			print(e) # Temp
			# Handle exitcode
			self.halt_thread(pid, tid, 255)

	def interrupt(self, iid, pid, tid):

		"""Call a computer interrupt.
		   Args: iid -> the interrupt ID to call
				 pid -> the process ID
				 tid -> the thread ID"""

		try:
			self.processes[pid].threads[tid].waiting = True
			# Wait until the CPU has finished the thread (and registers are committed)
			while True:
				ready = True
				for cpu in self.computer.cpu.cores:
					try:
						if cpu.pname == ('proc', pid) and cpu.tid == tid:
							ready = False
					except:
						pass
				if ready:
					break

			# Run the interrupt (NOTE: all interrupts must call update_process_memory_global after modifying memory)
			# NOTE: All interrupt calls must modify memory in the processes memory data, not global memory data. Using the method update_process_memory_global, memory can be synced up with all processes. 
			# Call the interrupt
			exitcode = self.computer.interrupt(iid, pid, tid)
			# Update memory in process
			self.update_process_memory_global(pid, tid)
			# In case of errors, set the pidtid to not running/error
			self.processes[pid].threads[tid].waiting = False
			# Check for errors
			if exitcode[0] != 0:
				# Handle exitcode
				self.halt_thread(pid, tid, exitcode[0])
		except Exception as e:
			print(e) # Temp
			# Handle exitcode
			self.halt_thread(pid, tid, 255)

	def execute_core(self, threads, core_id):

		"""Execute the threads on a CPU core.
		   Args: threads -> the thread TIDs and process PIDs to run
		         core_id -> the core ID to run the threads on"""

		# Iterate over each thread
		for pid, tid in threads:
			# Check if the thread is waiting for IO or is done
			if self.processes[pid].threads[tid].waiting or not self.processes[pid].threads[tid].running:
				continue
			# Get the thread data
			registers = self.processes[pid].threads[tid].registers
			processmemory = self.processes[pid].get_processmemory_thread(tid)
			# Load memory
			self.computer.memory.edit_memory_partition(('proc', pid), processmemory)
			# Load the correct core
			self.computer.cpu.init_core(core_id, processmemory, ('proc', pid), tid)
			if registers:
				self.computer.cpu.cores[core_id].registers = registers
			else:
				self.processes[pid].threads[tid].registers = self.computer.cpu.cores[core_id].registers
			# Run the core for a certain number of operations
			self.computer.cpu.begin_execute_core_num(core_id, self.max_operations_per_thread)
			self.computer.cpu.await_execution(core_id)
			# Update process processmemory
			self.processes[pid].update_global_pm(self.computer.cpu.cores[core_id].processmemory)
			self.processes[pid].update_thread_stack(tid, self.computer.cpu.cores[core_id].processmemory.stack)
			self.processes[pid].update_thread_registers(tid, self.computer.cpu.cores[core_id].registers)
			# Check for ending
			if hasattr(self.computer.cpu.cores[core_id], 'output_exit') and not self.processes[pid].threads[tid].waiting:
				self.processes[pid].threads[tid].running = False
				self.processes[pid].threads[tid].output = self.computer.cpu.get_return(core_id)
				# Check for process error
				if self.processes[pid].threads[tid].output[0] != 0:
					# Set process error
					self.processes[pid].state = 't'
					self.processes[pid].output = self.processes[pid].threads[tid].output
				# Check for process ending
				elif not all([self.processes[pid].threads[t].running for t in self.processes[pid].threads]):
					# All threads are done
					self.processes[pid].state = 't'
					self.processes[pid].output = (0, None)
			# Unload the core
			self.computer.cpu.unload_core(core_id)

	def _process_mainloop(self):

		"""Main process running loop. Should be run on a separate thread."""

		self.running = True
		# Main loop
		while self.running:
			# Split threads up for each CPU core
			num_cores = len(self.computer.cpu.cores)
			split_threads = [[] for i in range(num_cores)]
			current_core_num = 0
			# Go through each process
			for pid in self.processes:
				if self.processes[pid].state == 't':
					continue
				# Go through each thread
				for tid in self.processes[pid].threads:
					# Add this PID and TID to the according core
					split_threads[current_core_num].append((pid, tid))
				# Loop the current core number
				current_core_num += 1
				if current_core_num >= num_cores:
					current_core_num = 0

			executor_threads = []
			# Run the threads
			for core_id, threads in enumerate(split_threads):
				executor_thread = threading.Thread(target=self.execute_core, args=(threads, core_id))
				executor_threads.append(executor_thread)
				executor_thread.start()
				
			# Wait until all threads are finished running
			for executor_thread in executor_threads:
				executor_thread.join()

	def process_mainloop(self):

		"""Main process running loop."""

		# Start the process mainloop
		pm_thread = threading.Thread(target=self._process_mainloop)
		pm_thread.start()

	def start_os(self):

		"""Begin the operating system."""

		# Initialize all peripherals
		for peripheral_id, peripheral in self.computer.peripherals.items():
			peripheral.start(peripheral_id)

		# Start the process main loop
		self.process_mainloop()

	def stop_os(self):

		"""Stop the operating system."""

		# Kill all processes
		for pid in self.processes:
			self.process_terminate(pid)

		# Stop the process loop
		self.running = False

		# Stop all peripherals
		for peripheral_id, peripheral in self.computer.peripherals.items():
			peripheral.end()

	def __repr__(self):

		"""Get the string representation of the OS."""

		return "<OperatingSystem>"

	def __str__(self):

		"""Get the string representation of the OS."""

		return self.__repr__()

class Screen:
	pass

class Compiler:
	pass

class IO:
	pass

class Peripheral:
	
	"""The base class for all peripherals."""

	defined_interrupts = []

	def __init__(self, computer):

		"""Create the peripheral."""

		self.computer = computer

	def start(self, pid):

		"""Run starting or initialization protocols.
		   Args: pid -> peripheral ID"""

		self.pid = pid

	def end(self):

		"""Run ending protocols."""

		del self.pid

	def handle(self, iid, pid, tid):

		"""Handle the interrupt.
		   Args: iid -> the interrupt ID
		         pid -> the process ID
		         tid -> the thread ID"""

		...


class DisplayerTest(Peripheral):

	"""A temporary class to serve as a displayer peripheral."""

	defined_interrupts = [0x64]

	def start(self, pid):

		"""Run starting or initialization protocols.
		   Args: pid -> peripheral ID"""

		self.pid = pid
		self.computer.memory.add_memory_partition(('perp', self.pid), MemorySection('displayer_data', 10, b' ' * 10))

	def end(self):

		"""Run ending protocols."""

		del self.pid

	def handle(self, iid, pid, tid):

		if iid == 0x64:
			# print
			# get the data
			data = self.computer.memory.memorypartitions[('perp', self.pid)].data
			print(str(data, ENCODING))
			return (0, None)

class FPU:

	pass

class GPU:
	pass

class Process:

	"""The main process object."""

	def __init__(self, processmemory, threads, state):

		"""Create the process.
		   Args: processmemory -> the process memory for the process
		         threads -> a dictonary containing all the thread ids and the threads
		         state -> string containing the state of the process. 'r' for running, or 't' for terminated/stopped/error"""

		self.processmemory = processmemory
		self.threads = threads
		self.state = state

	def get_processmemory_thread(self, tid):

		"""Get the process memory for a specific thread.
		   Args: tid -> the thread id"""

		stack = self.threads[tid].stack
		newpm = copy.deepcopy(self.processmemory)
		newpm.stack = stack

		return newpm

	def get_registers_thread(self, tid):

		"""Get the registers for a certain thread.
		   Args: tid -> the thread id"""

		return self.threads[tid].registers

	def update_thread_stack(self, tid, stack):

		"""Update the stack for a certain thread. This is to be called after each thread finishes.
		   Args: tid -> the thread id of the thread
		         stack -> the stack to update to"""

		self.threads[tid].stack = stack

	def update_thread_registers(self, tid, registers):

		"""Update the registers for a certain thread. This is to be called after each thread finishes.
		   Args: tid -> the thread id of the thread
		         registers -> the registers to update to"""

		self.threads[tid].registers = registers

	def update_global_pm(self, processmemory):

		"""Update the global process process memory.
		   Args: processmemory -> the processes memory."""

		self.processmemory = processmemory

	def __repr__(self):

		"""Get the string representation of the process."""

		if hasattr(self, 'pid'):
			return "<Process PID " + str(self.pid) + " state " + self.state.upper() + ">"

		return "<Process state " + self.state.upper() + ">"

	def __str__(self):

		"""Get the string representation of the process."""

		return self.__repr__()


class PThread:
	
	"""The main thread object."""

	def __init__(self, tid, stack, registers):

		"""Create the thread.
		   Args: tid -> the thread id
		         stack -> this thread's stack data. will be replaced when the thread runs.
		         registers -> the registers for the thread"""

		self.tid = tid
		self.stack = stack
		self.registers = registers
		self.waiting = False
		self.running = True

	def __repr__(self):

		"""Get the string representation of the process."""

		return "<PThread tid " + str(self.tid) + " running " + self.running + ">"

	def __str__(self):

		"""Get the string representation of the process."""

		return self.__repr__()


class Terminal:

	"""The terminal class. Has a shell, which can cause different commands to be run. These will display the processes STDOut and input the STDIn."""

	pass

class ConsoleDisplay:

	"""The base class for a console display."""

	def __init__(self, computer, ):

		"""Create the console."""

		pass

	def set_view(self, pid):

		pass


class STDOut:

	"""The basic standard output class. Each process gets a standard output handle. The output gets mapped into the terminal/console."""

	def __init__(self, pid):

		"""Create the standard output."""

		self.pid = pid
		self.data = bytearray()

	def set_data(self, data):

		"""Set the data for the output stream."""

		self.data = data

	def write(self, data):

		"""Write data into the output stream."""

		self.data += data

	def pipe(self):

		"""Pipe/return the output stream."""

		return self.data

class STDIn:

	"""The basic standard input class."""


print('CREATING CODE')
print()
# This code counts to 100 (chr 'd') in the DATA section
code2 = bytearray(b'\x01\x01\x00\n\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x01\x01\x00\n\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x18\x01\x00\n\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x64\x1a\x02\x04\x00\x00\x00\x00\x00\x00\x00')
# code = bytearray(b'\x00\x01\x00\x05\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x04\x00\x00\x00\x0b\x02\x04\x00\x00\x00\x08\x00\x00\x00\x17\x02\x04\x00\x00\x004\x00\x00\x00!\x0c\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x0c\x00\x03\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x01\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x00\x03\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x00\x01\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x0b\x00\x01\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x17\x02\x04\x00\x00\x003\x00\x00\x00')
# code = bytearray(b'\x00\x01\x00\x05\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x04\x00\x00\x00"\x02\x04\x00\x00\x00*\x00\x00\x00!\x02\x00\x05\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x0c\x00\x00\x00\x00\x06\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x01\x01\x00\x06\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x01\x01\x02\x04\x00\x00\x00}\x00\x00\x00\x02\x01\x00\x00\x00\x04#')
# code = bytearray(b'\x00\x01\x00\x05\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x04\x00\x00\x00"\x02\x04\x00\x00\x00?\x00\x00\x00\x0c\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04!\x02\x01\x00\x00\x00\x00\x02\x00\x05\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x04\x00\x00\x00\x00\x06\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x01\x01\x00\x06\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x01\x01\x02\x04\x00\x00\x00\x92\x00\x00\x00\x02\x01\x00\x00\x00\x04#')
# code = bytearray(b'\x00\x01\x00\x0b\x02\x01\x00\x00\x00\x04\x02\x01\x00\x00\x00\x04\x01\x02\x04\x00\x00\x00G\x00\x00\x00\x02\x01\x00\x00\x00\x02\x01\x02\x04\x00\x00\x00:\x00\x00\x00\x01\x02\x04\x00\x00\x00G\x00\x00\x00\x02\x01\x00\x00\x00\x02')
# print(code)
# This code calls system interrupt 01
# code = bytearray(b'\x00\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x01\x00\x00\x00$')
# This code calls system interrupt 02
# code = b'\x00\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x02\x00\x00\x00$\x00\x01\x02\x04\x00\x00\x008\x00\x00\x00\x02\x01\x00\x00\x00\x01\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x01'
# This code also calls system interrupt 02 but dosen't do anything else
# code = bytearray(b'\x00\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x02\x00\x00\x00$')
# This code puts "Hello!" into peripheral 1's memory
code = b'\x00\x04\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x06\x01\x02\x04\x00\x00\x00+\x00\x00\x00\x02\x01\x00\x00\x00\x06(\x02\x01\x00\x00\x00d'
# code2 = bytearray(b'\x00\x00\x00\x02\x01\x00\x00\x00\x00\x02\x01\x00\x00\x00\x04\x02\x04\x00\x00\x00\x00\x00\x00\x00$')
print('CREATING PROCESS MEMORY')
# processmemory = ProcessMemory(code, b'd\x00\x00\x00<\x00\x00\x00', b'')
processmemory = ProcessMemory(code, b'Hello!', b'')
processmemory2 = ProcessMemory(code2, b'\x00\x00\x00\x00', b'')
print(processmemory)
print()
print("CREATING MEMORY")
memory = Memory()
print()
print("CREATING COMPUTER")
computer = Computer()
computer.set_memory(memory)
operatingsystem = OperatingSystem(computer)
testwriter = DisplayerTest(computer)
computer.add_peripheral(testwriter)
computer.set_os(operatingsystem)
print()
print("CREATING CPU")
cpu = CPU(computer, memory)
computer.set_cpu(cpu)
print()
print('CREATING CPU CORES')
core = CPUCore(cpu)
cid = cpu.add_core(core)
core2 = CPUCore(cpu)
cid2 = cpu.add_core(core2)
print(core, core2)
print()
print('CREATING PROCESSES')
t = PThread(0, MemorySection('stack', 0, b''), None)
p = Process(processmemory, {0 : t}, 't')
t2 = PThread(0, MemorySection('stack', 0, b''), None)
p2 = Process(processmemory2, {0 : t2}, 't')
print()
print('RUNNING OPERATING SYSTEM')
computer.operatingsystem.start_os()
# time.sleep(0.1)
pid = computer.operatingsystem.process_create(p)[1]
pid2 = computer.operatingsystem.process_create(p2)[1]

# time.sleep(1)
# pid2 = computer.operatingsystem.process_create(p2)[1]

print()
print('RUNNING PROCESS')

computer.operatingsystem.process_await(pid2)
print()
print('FINISHED PROCESS')
print()
print(computer.operatingsystem.processes)
print(computer.memory.memorypartitions[('proc', 1)].stack.data)
print(computer.memory.memorypartitions[('proc', 1)].data.data)
# computer.operatingsystem.process_await(pid2)
# print(computer.operatingsystem.processes[1].threads[0].output)
# print(computer.memory.memorypartitions[('proc', 1)].stack.data)
print(computer.operatingsystem.processes[1].output)
computer.operatingsystem.process_await(pid)
print(computer.operatingsystem.processes)
print(computer.operatingsystem.processes[0].processmemory.stack.data)
print(computer.operatingsystem.processes[0].output)
computer.operatingsystem.stop_os()
