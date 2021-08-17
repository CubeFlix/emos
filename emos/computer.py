"""

- EMOS 'computer.py' Source Code -

(C) Cubeflix 2021 (EMOS)

"""


# Imports
from misc import *
from memory import *


class FileSystem:

	"""A hard drive managed by the OS."""

	def __init__(self, computer, outfile):

		"""Create the hard drive.
		   Args: computer -> the computer the hard drive is attached to
		         outfile -> the name of the output file/virtual hard disk"""

		self.computer = computer
		self.outfile = outfile
		self.filesystem = {}

	def read_file(self, path):

		"""Read a file from the file system.
		   Args: path -> the path to the file"""

		# Split the path
		split_path = os.path.normpath(path).split(os.path.sep)
		# Find the file by iterating through the path into the file system
		traversal_history = [self.filesystem]
		for item in split_path:
			if item in ('', '.'):
				continue
			elif item == '..':
				if len(traversal_history) == 1:
					return (31, "Cannot traverse back from root directory.")
				# Move back
				del traversal_history[-1]
			# Traverse to the next section
			try:
				traversal_history.append(traversal_history[-1][item])
			except (KeyError, TypeError):
				return (32, "Path is invalid.")
		# Get the final file
		if not type(traversal_history[-1]) in (bytes, bytearray):
			return (32, "Path is invalid.")
		return (0, traversal_history[-1])

	def write_file(self, path, data):

		"""Write to a new or existing file on the file system.
		   Args: path -> the path to the file
		         data -> the data to write to the file"""

		# Split the path
		split_path = os.path.normpath(path).split(os.path.sep)
		final_name = split_path.pop()
		if any([char in final_name for char in INVALID_FILENAME_CHARS]):
			return (34, "Invalid filename.")
		# Find the file by iterating through the path into the file system
		traversal_history = [self.filesystem]
		for item in split_path:
			if item in ('', '.'):
				continue
			elif item == '..':
				if len(traversal_history) == 1:
					return (31, "Cannot traverse back from root directory.")
				# Move back
				del traversal_history[-1]
			# Traverse to the next section
			try:
				traversal_history.append(traversal_history[-1][item])
			except (KeyError, TypeError):
				return (32, "Path is invalid.")
		# Check for a folder
		if final_name in traversal_history[-1] and type(traversal_history[-1][final_name]) == dict:
			return (32, "Path is invalid.")
		# Write to the final file
		traversal_history[-1][final_name] = data
		# Update
		self._backend_update()
		return (0, None)

	def delete_file(self, path):

		"""Delete a file from the file system.
		   Args: path -> the path to the file"""

		# Split the path
		split_path = os.path.normpath(path).split(os.path.sep)
		# Find the file by iterating through the path into the file system
		traversal_history = [self.filesystem]
		for item in split_path:
			if item in ('', '.'):
				continue
			elif item == '..':
				if len(traversal_history) == 1:
					return (31, "Cannot traverse back from root directory.")
				# Move back
				del traversal_history[-1]
			# Traverse to the next section
			try:
				traversal_history.append(traversal_history[-1][item])
			except (KeyError, TypeError):
				return (32, "Path is invalid.")
		# Check the final file
		if not type(traversal_history[-1]) in (bytes, bytearray):
			return (32, "Path is invalid.")
		# Check for environment file
		if split_path[-1] == '__enviro':
			return (41, "Cannot delete environment file.")
		# Delete the file using the second to last reference in the traversal history
		del traversal_history[-2][split_path[-1]]
		# Update
		self._backend_update()
		return (0, None)

	def rename_file(self, path, new_name):

		"""Rename a file within the file system.
		   Args: path -> the path to the file
		         new_name -> new file name"""

		if any([char in new_name for char in INVALID_FILENAME_CHARS]):
			return (34, "Invalid filename.")
		# Split the path
		split_path = os.path.normpath(path).split(os.path.sep)
		# Find the file by iterating through the path into the file system
		traversal_history = [self.filesystem]
		for item in split_path:
			if item in ('', '.'):
				continue
			elif item == '..':
				if len(traversal_history) == 1:
					return (31, "Cannot traverse back from root directory.")
				# Move back
				del traversal_history[-1]
			# Traverse to the next section
			try:
				traversal_history.append(traversal_history[-1][item])
			except (KeyError, TypeError):
				return (32, "Path is invalid.")
		# Allow folders and files
		# Rename the file using the second to last reference in the traversal history
		# Check for environment file
		if split_path[-1] == '__enviro':
			return (41, "Cannot delete environment file.")
		traversal_history[-2][new_name] = traversal_history[-2].pop(split_path[-1])
		# Update
		self._backend_update()
		return (0, None)

	def create_directory(self, path):

		"""Create a directory in the file system.
		   Args: path -> the path to the folder"""

		# Split the path
		split_path = os.path.normpath(path).split(os.path.sep)
		final_name = split_path.pop()
		if any([char in final_name for char in INVALID_FILENAME_CHARS]):
			return (34, "Invalid directory name.")
		# Find the folder by iterating through the path into the file system
		traversal_history = [self.filesystem]
		for item in split_path:
			if item in ('', '.'):
				continue
			elif item == '..':
				if len(traversal_history) == 1:
					return (31, "Cannot traverse back from root directory.")
				# Move back
				del traversal_history[-1]
			# Traverse to the next section
			try:
				traversal_history.append(traversal_history[-1][item])
			except (KeyError, TypeError):
				return (32, "Path is invalid.")
		# Check for an existing folder
		if final_name in traversal_history[-1] and type(traversal_history[-1][final_name]) == dict:
			return (33, "Folder already exists.")
		# Check for an existing file
		if final_name in traversal_history[-1] and type(traversal_history[-1][final_name]) in (bytes, bytearray):
			return (32, "Path is invalid.")
		# Create the directory
		traversal_history[-1][final_name] = {}
		# Update
		self._backend_update()
		return (0, None)

	def delete_directory(self, path):

		"""Delete a directory from the file system.
		   Args: path -> the path to the folder"""

		# Split the path
		split_path = os.path.normpath(path).split(os.path.sep)
		# Find the folder by iterating through the path into the file system
		traversal_history = [self.filesystem]
		for item in split_path:
			if item in ('', '.'):
				continue
			elif item == '..':
				if len(traversal_history) == 1:
					return (31, "Cannot traverse back from root directory.")
				# Move back
				del traversal_history[-1]
			# Traverse to the next section
			try:
				traversal_history.append(traversal_history[-1][item])
			except (KeyError, TypeError):
				return (32, "Path is invalid.")
		# Check the final directory
		if not type(traversal_history[-1]) == dict:
			return (32, "Path is invalid.")
		# Delete the folder using the second to last reference in the traversal history
		try:
			del traversal_history[-2][split_path[-1]]
		except Exception as e:
			return (32, "Path is invalid.")
		# Update
		self._backend_update()
		return (0, None)

	def list_directory(self, path):

		"""List a directory path, seperated by newlines.
		   Args: path -> the path to the directory"""

		# Split the path
		split_path = os.path.normpath(path).split(os.path.sep)
		# Find the folder by iterating through the path into the file system
		traversal_history = [self.filesystem]
		for item in split_path:
			if item in ('', '.'):
				continue
			elif item == '..':
				if len(traversal_history) == 1:
					return (31, "Cannot traverse back from root directory.")
				# Move back
				del traversal_history[-1]
			# Traverse to the next section
			try:
				traversal_history.append(traversal_history[-1][item])
			except (KeyError, TypeError):
				return (32, "Path is invalid.")
		# Check the final directory
		if not type(traversal_history[-1]) == dict:
			return (32, "Path is invalid.")
		# List the folder
		data = '\n'.join(traversal_history[-1])
		# Update
		self._backend_update()
		return (0, data)

	def get_full_buffer(self):

		"""Get the full file system buffer."""

		return pickle.dumps([self.filesystem, self.password])

	def _backend_load(self):

		"""Load the file system from the output file."""

		try:
			f = open(self.outfile, 'rb')
		except Exception as e:
			raise SysError("Output file for FileSystem does not exist.")
		self.filesystem, self.password = pickle.loads(f.read())
		f.close()

		if not '__enviro' in self.filesystem:
			self.filesystem['__enviro'] = b'{}'

		self._backend_update()

	def _backend_update(self):

		"""Update the virtual hard drive file."""

		f = open(self.outfile, 'wb')
		f.write(self.get_full_buffer())
		f.close()

	def _format(self, password=None):

		"""Format the hard drive."""

		self.filesystem = {'__enviro' : b'{}'}
		self.password = hashlib.sha256(bytes(password, ENCODING)).digest()
		self._backend_update()


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

	def set_filesystem(self, filesystem):

		"""Set the file system/hard drive for the computer.
		   Args: filesystem -> the file system to set"""

		self.filesystem = filesystem

	def start(self):

		"""Start up the computer."""

		self.operatingsystem.start_os()

	def shutdown(self):

		"""Shut down the computer."""

		# NOTE: To avoid errors with user-side shutdown, terminals and other peripherals should not be used after the shutdown,
		# and processes should not be accessed either, apart from debugging purposes.

		self.operatingsystem.stop_os()

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


class Peripheral:
	
	"""The base class for all peripherals."""

	defined_interrupts = []

	def __init__(self, computer):

		"""Create the peripheral.
		   Args: computer -> computer the peripheral is attached to"""

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

	def __repr__(self):

		"""Get the string representation of the peripheral."""

		return "<Peripheral>"

	def __str__(self):

		"""Get the string representation of the peripheral."""

		return self.__repr__()


class TerminalScreen(Peripheral):

	"""The terminal screen class."""

	defined_interrupts = [0xe0, 0xe1, 0xe2]

	def __init__(self, computer):

		"""Create the terminal."""

		self.computer = computer

	def start(self, pid):

		"""Start the terminal.
		   Args: pid -> peripheral ID"""

		self.pid = pid

		# Get screen size
		size = os.get_terminal_size()
		self.rows = size.lines
		self.cols = size.columns
		
		# Create the designated memory for the terminal's printout
		self.computer.memory.add_memory_partition(('perp', self.pid), MemorySection('terminal_perp_' + str(self.pid), self.rows * self.cols + self.rows, bytes(self.rows * self.cols + self.rows)))

	def end(self):

		"""Run ending protocols."""

		# Remove the designated memory for the terminal's printout
		self.computer.memory.delete_memory_partition(('perp', self.pid))

		del self.pid
		del self.rows
		del self.cols

	def handle(self, iid, pid, tid):

		"""Handle the interrupt.
		   Args: iid -> the interrupt ID
		         pid -> the process ID
		         tid -> the thread ID"""

		if iid == 0xe0:
			# Update the screen with the new buffer
			return self.update_screen()
		elif iid == 0xe1:
			# Get one char and save it to RAX
			char = getchars(1)
			# Place the char in RAX
			self.computer.operatingsystem.processes[pid].threads[tid].registers['RAX'].data[0] = ord(char)
			return (0, None)
		elif iid == 0xe2:
			# Get a number of chars (as specified in RBX) and put them into stack
			nchars = int.from_bytes(self.computer.operatingsystem.processes[pid].threads[tid].registers['RBX'].data[0 : 4], byteorder='little')
			chars = getchars(nchars)
			# Place the chars
			self.computer.operatingsystem.processes[pid].threads[tid].stack.push(bytes(chars, ENCODING))
			# Recalculate RES
			self.computer.operatingsystem.processes[pid].threads[tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.computer.operatingsystem.processes[pid].threads[tid].stack.data) + self.computer.operatingsystem.processes[pid].ss, 4, byteorder='little')
			return (0, None)
	
	def update_screen(self):

		"""Update the data buffer to the screen."""

		# Clear the terminal
		clear()

		# Get a variable for the data
		data = str(self.computer.memory.memorypartitions[('perp', self.pid)].data.replace(b'\x00', b''), ENCODING)

		new_data = []

		# Put in newlines if a line is too long
		for line in data.split('\n'):
			if len(line) > self.cols:
				# Too many characters in the line
				new_data.append(line[ : self.cols])
				new_data.append(line[self.cols : ])
			else:
				# Else, just add the line
				new_data.append(line)

		# Join the new data
		data = '\n'.join(new_data)

		# Cut the data off if there are too many newlines
		if data.count('\n') + 1 > self.rows:
			# Too many lines, so cut some off
			split_data = data.split('\n')
			new_data = []
			# Iterate over each line, reversed
			for line in reversed(split_data):
				# Check if the line is too long
				if len(line) > self.cols:
					# Add two lines
					new_data.append(line[ : self.cols])
					new_data.append(line[self.cols : ])
				else:
					# Add the line
					new_data.append(line)
				# If there are too many lines
				if len(new_data) >= self.rows:
					break

			# Join the new data, reversed
			data = '\n'.join(reversed(new_data))

		# Print the data
		write(data)

		return (0, None)

	def __repr__(self):

		"""Get the string representation of the peripheral."""

		return "<TerminalScreen>"

	def __str__(self):

		"""Get the string representation of the peripheral."""

		return self.__repr__()
