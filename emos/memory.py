"""

- EMOS 'memory.py' Source Code -

(C) Cubeflix 2021 (EMOS)

"""


# Imports
from misc import *


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
		data = self.data[-4 : ]
		del self.data[-4 : ]
		self.size -= 4
		return (0, data)

	def push(self, data):

		"""Push bytes onto the memory."""

		self.data = self.data + data
		self.size += len(data)
		return (0, None)

	def popn(self, n):

		"""Pop n bytes from the memory.
		   Args: n -> number of bytes to pop"""

		if n == 0:
			return (0, b'')

		if self.size < n:
			# Size is less than n
			return (3, "Stack is not large enough.")
		data = self.data[-n : ]
		del self.data[-n : ]
		self.size -= n
		return (0, data)

	def removebytes(self, numbytes):

		"""Remove numbytes bytes from the end of the memory."""

		if self.size < numbytes:
			return (4, "Not enough memory to remove.")
		self.data = self.data[ : self.size - numbytes]
		self.size -= numbytes
		return (0, None)

	def get_bytes(self, offset, numbytes):

		"""Get bytes from the memory section.
		   Args: offset -> beginning offset
		         numbytes -> number of bytes to get"""

		if offset + numbytes > self.size:
			return (5, "Offset is not in memory.")

		return (0, self.data[offset : offset + numbytes])

	def set_bytes(self, offset, data):

		"""Set data to the memory section.
		   Args: offset -> offset to begin setting data at
		         data -> data to set"""

		if offset + len(data) > self.size:
			return (5, "Offset is not in memory.")

		self.data = self.data[ : offset] + data + self.data[offset + len(data) : ]
		self.size += len(data)

		return (0, None)

	def __repr__(self):

		"""Get the string representation of the memory."""

		return "<MemorySection " + str(self.name) + ">"

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

		currentOffset = 0
		# Loop to find the byte
		for name, memorypartition in self.memorypartitions.items():
			lastOffset = currentOffset
			# Check if the current base works
			if type(memorypartition) == ProcessMemory:
				currentOffset -= memorypartition.es
			elif type(memorypartition) == MemorySection:
				currentOffset -= memorypartition.size

			if currentOffset <= 0:
				if type(memorypartition) == ProcessMemory:
					return memorypartition.get_byte(lastOffset)
				elif type(memorypartition) == MemorySection:
					return (0, memorypartition.data[lastOffset])
				
		# Not in memory
		return (5, "Offset not in memory.")

	def set_byte(self, offset, byte):

		"""Set a single byte to memory at offset offset.
		   Args: offset -> the offset to set the byte to
		         byte -> the byte to set"""

		currentOffset = 0
		# Loop to find the byte
		for name, memorypartition in self.memorypartitions.items():
			lastOffset = currentOffset
			# Check if the current base works
			if type(memorypartition) == ProcessMemory:
				currentOffset -= memorypartition.es
			elif type(memorypartition) == MemorySection:
				currentOffset -= memorypartition.size
			# Set the byte
			if currentOffset <= 0:
				if type(memorypartition) == ProcessMemory:
					return self.memorypartitions[name].set_byte(lastOffset, byte)
				elif type(memorypartition) == MemorySection:
					self.memorypartitions[name].data[lastOffset] = byte
					return (0, None)

		# Not in memory
		return (5, "Offset not in memory.")

	def get_bytes(self, offset, length):

		"""Get bytes from memory with offset offset and length length.
		   Args: offset -> offset to get the bytes from
		         length -> length of data to get"""

		data = bytearray()
		# Loop over each byte
		for i in range(offset, offset + length):
			# Get byte
			byte = self.get_byte(i)
			if byte[0] != 0:
				# Error
				return byte
			# Add the data
			data += bytearray([byte[1]])
		# Return the data
		return (0, data)

	def set_bytes(self, offset, data):

		"""Get bytes from memory with offset offset and length length.
		   Args: offset -> offset to get the bytes from
		         length -> length of data to get"""

		# Loop over each byte
		for i, byte in data:
			# Get byte
			exitcode = self.set_byte(i + offset, byte)
			if exitcode[0] != 0:
				# Error
				return exitcode

		return (0, None)

	def __repr__(self):

		"""Get the string representation of the memory."""

		return "<Memory size " + hex(self.size) + " with " + str(len(self.memorypartitions)) + " partition(s)>"

	def __str__(self):

		"""Get the string representation of the memory."""

		return self.__repr__()
