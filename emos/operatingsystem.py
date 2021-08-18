"""

- EMOS 'operatingsystem.py' Source Code -

(C) Cubeflix 2021 (EMOS)

"""


# Imports
from misc import *
from memory import *
from cpu import *
from computer import *


class OperatingSystem:

	"""The main operating system or OS the computer uses. System calls through interrupts can allow for memory and process management (heap and process memory), along with other things such as IO (BIOS).
	   The OS also handles files and process management with memory, ensuring that we don't run out. Finally, the OS can also switch into user mode, letting the user control everything."""

	def __init__(self, computer, has_password=True):

		"""Create the operating system.
		   Args: computer -> the computer the operating system is installed on
		         has_password -> does the operating system use a password"""

		self.computer = computer
		self.has_password = has_password

		self.mem_alloc_ids = []

		self.process_ids = []
		self.processes = {}

		self.running = False

		# Maximum number of operations to run on each thread if no IO is involved
		self.max_operations_per_thread = 64

		# Terminal
		self.terminal = Terminal(self.computer)
		# Kernel STDOut
		self.kernel_stdout = STDOut()

		# System libraries (TODO)
		self.syslibs = [INT_STR_LIB, WRITELIB]

		self.log = ''

	def set_cmd_handler(self, cmdhandler):

		"""Set the current command handler. This is optional.
		   Args: cmdhandler -> the command handler to use"""

		self.cmdhandler = cmdhandler

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

		self.computer.memory.add_memory_partition(('mem', current_mem_id), MemorySection(('mem', current_mem_id), 0, bytearray()))
		self.mem_alloc_ids.append(current_mem_id)
		return (0, current_mem_id)

	def free_memory(self, mem_id):

		"""Free the memory at memory id mem_id.
		   Args: mem_id -> memory id"""

		if not mem_id in self.mem_alloc_ids:
			return (19, "Memory ID does not exist.")

		# Free the memory
		self.mem_alloc_ids.remove(mem_id)
		self.computer.memory.delete_memory_partition(('mem', mem_id))

		return (0, None)

	def get_memory_size(self, mem_id):

		"""Get the size of the memory partition mem_id.
		   Args: mem_id -> memory id"""

		if not mem_id in self.mem_alloc_ids:
			return (19, "Memory ID does not exist.")

		return (0, self.computer.memory.memorypartitions[('mem', mem_id)].size)

	def get_memory(self, mem_id, start_offset, size):

		"""Get memory mem_id at start_offset with size size.
		   Args: mem_id -> memory id
		   		 start_offset -> starting offset
		   		 size -> amount of memory to get"""

		if not mem_id in self.mem_alloc_ids:
			return (19, "Memory ID does not exist.")

		return self.computer.memory.memorypartitions[('mem', mem_id)].get_bytes(start_offset, size)

	def edit_memory(self, mem_id, data, start_offset):

		"""Edit the memory at mem_id, and move data into the memory at start_offset.
		   Args: mem_id -> memory id
		   		 data -> data to edit to
		   		 start_offset -> starting offset"""

		# Get size
		exitcode, size = self.get_memory_size(mem_id)
		if exitcode != 0:
			return (exitcode, size)

		# Get data
		exitcode, current_data = self.get_memory(mem_id, 0, size)
		if exitcode != 0:
			return (exitcode, current_data)

		# Too large, but starts within bounds
		if start_offset + len(data) > size and start_offset < size:
			new_data = current_data[ : start_offset] + data
		# Too large, and starts out of bounds (padding with zero bytes)
		elif start_offset + len(data) > size and start_offset > size:
			new_data = current_data + bytes(start_offset - size) + data
		# Within bounds
		else:
			# New data
			new_data = current_data[ : start_offset] + data + current_data[start_offset + len(data) : ]

		return self.computer.memory.edit_memory_partition(('mem', mem_id), MemorySection(self.computer.memory.memorypartitions[('mem', mem_id)].name, len(new_data), new_data))

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
		self.processes[current_pid].initialize(self.computer)

		return (0, current_pid)

	def thread_create(self, pid, thread):

		"""Create a thread in a process, returning the TID.
		   Args: pid -> the process ID to add to
		         thread -> the thread to use"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		self.processes[pid].threads[len(self.processes[pid].threads)] = thread
		self.processes[pid].threads[len(self.processes[pid].threads) - 1].tid = len(self.processes[pid].threads) - 1

		return (0, len(self.processes[pid].threads) - 1)

	def process_terminate(self, pid):

		"""Terminate a process.
		   Args: pid -> the process ID to terminate"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		self.processes[pid].state = 't'

		return (0, None)

	def process_resume(self, pid):

		"""Resume a terminated process.
		   Args: pid -> the process ID to resume"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		self.processes[pid].state = 'r'

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

		"""Terminate a thread.
		   Args: pid -> the process ID
		         tid -> the thread ID"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		if not tid in self.processes[pid].threads:
			return (21, "TID dosen't exist.")

		self.processes[pid].threads[tid].running = False

		return (0, None)

	def thread_resume(self, pid, tid):

		"""Resume a thread.
		   Args: pid -> the process ID
		         tid -> the thread ID"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		if not tid in self.processes[pid].threads:
			return (21, "TID dosen't exist.")

		self.processes[pid].threads[tid].running = True

		return (0, None)

	def thread_delete(self, pid, tid):

		"""Delete a thread.
		   Args: pid -> the process ID
		         tid -> the thread ID"""

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

		return self.process_create(copy.deepcopy(self.processes[pid]))

	def thread_fork(self, pid, tid):

		"""Fork a thread.
		   Args: pid -> the process ID
		         tid -> the thread ID to fork"""

		if not pid in self.process_ids:
			return (20, "PID doesn't exist.")

		if not tid in self.processes[pid].threads:
			return (21, "TID dosen't exist.")

		return self.thread_create(pid, copy.deepcopy(self.processes[pid].threads[tid]))

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

	def run_executable_data(self, data):

		"""Run executable data and load it, retuning the process.
		   Args: data -> data to run"""

		# Get the beginning data offset
		data_offset = int.from_bytes(data[0 : 4], byteorder='little')
		# Split the data
		data = data[4 : ]
		# Get the code section
		code_section = data[ : data_offset]
		# Get the data section
		data_section = data[data_offset : ]

		# Create the process memory
		processmemory = ProcessMemory(code_section, data_section, b'')

		# Create the thread
		thread = PThread(0, MemorySection('stack', 0, b''), None)

		# Create process
		process = Process(processmemory, {0 : thread}, 't')
		return process

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
			except Exception:
				pass

	def halt_thread(self, pid, tid, exitcode):

		"""Halt a thread.
		   Args: pid -> process id
		         tid -> thread id to halt"""

		# Terminate the program with exitcode
		self.processes[pid].threads[tid].output = (exitcode, None)
		e_exitcode = self.processes[pid].threads[tid].stack.set_data(self.processes[pid].threads[tid].stack.data + int.to_bytes(exitcode, 2, byteorder='little'))
		self.processes[pid].threads[tid].running = False
		if exitcode != 0:
			self.processes[pid].start = 't'
			self.processes[pid].output = (exitcode, None)
		if not all([self.processes[pid].threads[t].running for t in self.processes[pid].threads]):
			# All threads are done
			self.processes[pid].state = 't'
			self.processes[pid].output = (exitcode, None)
		return e_exitcode

	def systemcall(self, pid, tid):

		"""Preform a system call.
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
					except Exception:
						pass
				if ready:
					break
			# Get the system call ID
			syscallid = int.from_bytes(self.processes[pid].threads[tid].registers['RAX'].get_bytes(0, 4)[1], byteorder='little')
			
			# Run the system call (NOTE: all syscalls must call update_process_memory_global after modifying memory)
			# NOTE: All system calls must modify memory in the processes memory data, not global memory data. Using the method update_process_memory_global, memory can be synced up with all processes. 
			
			if syscallid == 0:
				# Terminate with exit code in RBX
				s_exitcode = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				exitcode = self.halt_thread(pid, tid, s_exitcode)
			elif syscallid == 1:
				# Write to the processes STDOut with the beginning offset in RBX, and the length in RCX
				begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
				# Get the data
				processmemory_use = self.processes[pid].get_processmemory_thread(tid)
				exitcode, data = processmemory_use.get_bytes(begin_offset, length)
				if exitcode != 0:
					exitcode = (exitcode, None)
				else:
					# Write the data to the STDOut
					exitcode = self.processes[pid].stdout.write(data, self.terminal)
			elif syscallid == 2:
				# Read from the processes STDIn with the length in RBX and save it to the thread's stack
				length = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				exitcode, data = self.processes[pid].stdin.readn(length, self.terminal)
				if exitcode != 0:
					exitcode = (exitcode, None)
				else:
					# Write the data in the stack
					self.processes[pid].threads[tid].stack.push(bytes(data, ENCODING))
					# Modify the processes registers
					self.processes[pid].threads[tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.processes[pid].threads[tid].stack.data) + self.processes[pid].processmemory.ss, 4, byteorder='little')
					exitcode = (0, None)
			elif syscallid == 3:
				# Take input from the processes STDIn, echoing back. Puts the length of the data into RAX
				exitcode, data = self.processes[pid].stdin.take_input(self.terminal)
				if exitcode != 0:
					exitcode = (exitcode, None)
				else:
					# Write the data in the stack
					self.processes[pid].threads[tid].stack.push(bytes(data, ENCODING))
					# Modify the processes registers
					self.processes[pid].threads[tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.processes[pid].threads[tid].stack.data) + self.processes[pid].processmemory.ss, 4, byteorder='little')
					self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(data), 4, byteorder='little')
					exitcode = (0, None)
			elif syscallid == 4:
				# Call a kernel panic
				# Check the process security level
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Enter kernel terminal mode
					self.terminal.kernel_mode()
					# Get the error code in RBX
					error_code = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					# Form the kernel data
					data = ''
					rows = self.computer.peripherals[self.terminalID].rows
					cols = self.computer.peripherals[self.terminalID].cols
					cent_text = ('KERNEL PANIC ERROR - ERROR CODE: ' + hex(error_code)).center(cols, '-')
					text = ('-' * cols + '\n') * (rows // 2) + cent_text + ('-' * cols + '\n') * (rows // 2 - 1)
					# Write to the kernel data
					self.kernel_stdout.write(bytes(text, ENCODING), self.terminal)
					# Kill all processes
					for process in self.processes:
						for thread in self.processes[process].threads:
							self.halt_thread(process, thread, 26) # Error code 26 (kernel panic)
						self.process_terminate(process)
					# Enter the infinite loop
					exitcode = (0, None)
					while True: pass
			elif syscallid == 5:
				# Fork the current process
				exitcode = self.process_fork(pid)
				if exitcode[0] == 0:
					# Put the PID into RBX
					self.processes[pid].threads[tid].registers['RAX'].data[0 : 4] = int.to_bytes(exitcode[1], 4, byteorder='little')
					# Set the other processes waiting attribute
					self.processes[exitcode[1]].theads[tid].waiting = False
					# Give the new process the exit code
					self.processes[exitcode[1]].threads[tid].registers['RAX'].data[0 : 4] = bytes(4)
			elif syscallid == 6:
				# Fork the current thread
				exitcode = self.thread_fork(pid, tid)
				if exitcode[0] == 0:
					# Put the TID into RBX
					self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(exitcode[1], 4, byteorder='little')
					# Set the other thread's waiting attribute
					self.processes[pid].threads[exitcode[1]].waiting = False
					# Give the new thread the exit code
					self.processes[pid].threads[exitcode[1]].registers['RAX'].data[0 : 4] = bytes(4)
			elif syscallid == 7:
				# Get the current PID and put it into RBX
				self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(pid, 4, byteorder='little')
				exitcode = (0, None)
			elif syscallid == 8:
				# Get the current TID and put it into RBX
				self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(tid, 4, byteorder='little')
				exitcode = (0, None)
			elif syscallid == 9:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Kill a process with PID in RBX and exitcode in RCX
					s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					s_exitcode = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					exitcode = self.process_terminate(s_pid)
					self.processes[s_pid].output = (0, s_exitcode)
			elif syscallid == 10:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Kill a thread with PID in RBX, TID in RCX, and exitcode in RDI
					s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					s_tid = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					s_exitcode = int.from_bytes(self.processes[pid].threads[tid].registers['RDI'].get_bytes(0, 4)[1], byteorder='little')
					exitcode = self.halt_thread(s_pid, s_tid, s_exitcode)
			elif syscallid == 11:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Delete a process from the records with the PID in RBX
					# Get the PID from RBX
					s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					exitcode = self.process_delete(s_pid)
			elif syscallid == 12:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Delete a thread from the records with the PID in RBX and the TID RCX
					# Get the PID from RBX
					s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					# Get the TID from RCX
					s_tid = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					exitcode = self.thread_delete(s_pid, s_tid)
			elif syscallid == 13:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Import a system dynamic library to the current thread, putting the ID into RBX
					# Get the LID (library ID) from RBX
					s_lid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					# Find the LID
					if s_lid < len(self.syslibs):
						# Import the library
						self.processes[pid].threads[tid].dynamic_libraries.append(self.syslibs[s_lid](self, pid, tid))
						# Put the LID into RBX
						self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(self.processes[pid].threads[tid].dynamic_libraries) - 1, 4, byteorder='little')
						exitcode = (0, None)
					else:
						# Invalid LID
						exitcode = (27, "Library ID is invalid.")
			elif syscallid == 14:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Call an imported dynamic library, with the LID in RBX and the call ID in RCX
					# Get the LID and call ID
					s_lid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					s_call = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					# Call the library
					if s_lid < len(self.processes[pid].threads[tid].dynamic_libraries):
						# Get the library
						lib = self.processes[pid].threads[tid].dynamic_libraries[s_lid]
						if s_call in lib.defined_calls:
							# Call the library
							exitcode = self.processes[pid].threads[tid].dynamic_libraries[s_lid].handle(s_call)
						else:
							# Invalid call ID
							exitcode = (28, "Call ID is invalid.")
					else:
						# Invalid LID
						exitcode = (27, "Library ID is invalid.")
			elif syscallid == 15:
				# Allocate heap memory, putting the ID in RBX
				exitcode = self.allocate_memory()
				if exitcode[0] == 0:
					self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(exitcode[1], 4, byteorder='little')
			elif syscallid == 16:
				# Free heap memory, with the ID in RBX
				s_id = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				exitcode = self.free_memory(s_id)
			elif syscallid == 17:
				# Get the length of a heap memory section with ID in RBX, putting the length in RBX
				s_id = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				# Get the length
				exitcode, s_length = self.get_memory_size(s_id)
				if exitcode == 0:
					self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(s_length, 4, byteorder='little')
					exitcode = (0, None)
				else:
					exitcode = (exitcode, None)
			elif syscallid == 18:
				# Get the size of the given STDIn data, putting the length into RBX
				self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(self.processes[pid].stdin.data), 4, byteorder='little')
				exitcode = (0, None)
			elif syscallid == 19:
				# Await a processes completion with the PID in RBX
				s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				exitcode = self.process_await(s_pid)
			elif syscallid == 20:
				# Await a thread's completion with the PID in RBX and the TID in RCX
				s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				s_tid = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
				exitcode = self.thread_await(s_pid, s_tid)
			elif syscallid == 21:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Create a process with the size of the code section in RBX and the size of the data section in RCX, putting the PID into RBX
					s_code = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					s_data = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					# Create the process object
					s_thread = PThread(0, MemorySection('stack', 0, b''), None)
					s_process = Process(ProcessMemory(bytes(s_code), bytes(s_data), b''), {0 : s_thread}, 't')
					# Create the process
					exitcode = self.process_create(s_process)
					if exitcode[0] == 0:
						# Successful process creation
						self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(s_length, 4, byteorder='little')
			elif syscallid == 22:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Resume a process with the PID in RBX
					s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					exitcode = self.process_resume(s_pid)
			elif syscallid == 23:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Resume a thread with the PID in RBX and TID in RCX
					s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					s_tid = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					exitcode = self.thread_resume(s_pid, s_tid)
			elif syscallid == 24:
				# Get a processes exit code with the PID in RBX putting the exitcode into RBX
				s_pid = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				if not s_pid in self.process_ids:
					exitcode = (20, "PID doesn't exist.")
				else:
					if not hasattr(self.processes[s_pid], 'output'):
						exitcode = (25, "Process is not finished.")
					else:
						self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(self.processes[s_pid].output[0], 4, byteorder='little')
						exitcode = (0, None)
			elif syscallid == 25:
				# Wait for RBX milliseconds
				s_time = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				time.sleep(s_time / 1000)
				exitcode = (0, None)
			elif syscallid == 26:
				# Change the current working directory (in the ProcessCMDHandler) with the string defined in RBX and RCX
				begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
				# Get the data
				processmemory_use = self.processes[pid].get_processmemory_thread(tid)
				exitcode, data = processmemory_use.get_bytes(begin_offset, length)
				exitcode = (exitcode, None)
				if exitcode[0] != 0:
					pass
				else:
					# Change the CWD
					path = str(data, ENCODING)
					if not (path.startswith('/') or path.startswith('\\')):
						current = os.path.normpath(self.processes[pid].cmdhandler.current_working_dir).split(os.path.sep)
						for section in os.path.normpath(path).split(os.path.sep):
							if section in ('', '.'):
								continue
							elif section == '..':
								if len(current) != 0:
									current.pop()
								else:
									exitcode = (31, "Cannot traverse back from root directory.")
									break
							else:
								current.append(section)
						if exitcode[0] == 0:
							self.processes[pid].cmdhandler.current_working_dir = '/'.join(current)
					else:
						self.processes[pid].cmdhandler.current_working_dir = path
			elif syscallid == 27:
				# Read a file given by RBX and RCX, and place it along with it's length into the stack and RBX, respectively
				begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
				# Get the data
				processmemory_use = self.processes[pid].get_processmemory_thread(tid)
				exitcode, data = processmemory_use.get_bytes(begin_offset, length)
				if exitcode != 0:
					exitcode = (exitcode, None)
				else:
					# Read the file
					path = str(data, ENCODING)
					if path.startswith('/') or path.startswith('\\'):
						# Absolute path
						fullpath = path
					else:
						# Relative path
						fullpath = os.path.join(self.processes[pid].cmdhandler.current_working_dir, path)
					exitcode = self.computer.filesystem.read_file(fullpath)
					if exitcode[0] == 0:
						# Write the data in the stack
						self.processes[pid].threads[tid].stack.push(exitcode[1])
						# Modify the processes registers
						self.processes[pid].threads[tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.processes[pid].threads[tid].stack.data) + self.processes[pid].processmemory.ss, 4, byteorder='little')
						self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(exitcode[1]), 4, byteorder="little")
			elif syscallid == 28:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Write to a file from the process memory given by R9 and R10, with the filename given by RBX and RCX
					begin_offset_filename = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					length_filename = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					begin_offset_data = int.from_bytes(self.processes[pid].threads[tid].registers['R9'].get_bytes(0, 4)[1], byteorder='little')
					length_data = int.from_bytes(self.processes[pid].threads[tid].registers['R10'].get_bytes(0, 4)[1], byteorder='little')
					# Get the data
					processmemory_use = self.processes[pid].get_processmemory_thread(tid)
					exitcode, data = processmemory_use.get_bytes(begin_offset_data, length_data)
					if exitcode != 0:
						exitcode = (exitcode, None)
					else:
						exitcode, filename = processmemory_use.get_bytes(begin_offset_filename, length_filename)
						if exitcode != 0:
							exitcode = (exitcode, None)
						else:
							# Write to the file
							path = str(filename, ENCODING)
							if path.startswith('/') or path.startswith('\\'):
								# Absolute path
								fullpath = path
							else:
								# Relative path
								fullpath = os.path.join(self.processes[pid].cmdhandler.current_working_dir, path)
							exitcode = self.computer.filesystem.write_file(fullpath, data)
			elif syscallid == 29:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Delete a file with the path given by RBX and RCX
					begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					# Get the data
					processmemory_use = self.processes[pid].get_processmemory_thread(tid)
					exitcode, data = processmemory_use.get_bytes(begin_offset, length)
					if exitcode != 0:
						exitcode = (exitcode, None)
					else:
						# Delete the file
						path = str(data, ENCODING)
						if path.startswith('/') or path.startswith('\\'):
							# Absolute path
							fullpath = path
						else:
							# Relative path
							fullpath = os.path.join(self.processes[pid].cmdhandler.current_working_dir, path)
						exitcode = self.computer.filesystem.delete_file(fullpath)
			elif syscallid == 30:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Rename a file with the path given by RBX and RCX, with the new name given by R9 and R10
					begin_offset_filename = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					length_filename = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					begin_offset_newname = int.from_bytes(self.processes[pid].threads[tid].registers['R9'].get_bytes(0, 4)[1], byteorder='little')
					length_newname = int.from_bytes(self.processes[pid].threads[tid].registers['R10'].get_bytes(0, 4)[1], byteorder='little')
					# Get the data
					processmemory_use = self.processes[pid].get_processmemory_thread(tid)
					exitcode, filename = processmemory_use.get_bytes(begin_offset_filename, length_filename)
					if exitcode != 0:
						exitcode = (exitcode, None)
					else:
						exitcode, newname = processmemory_use.get_bytes(begin_offset_newname, length_newname)
						if exitcode != 0:
							exitcode = (exitcode, None)
						else:
							# Rename the file
							path = str(filename, ENCODING)
							if path.startswith('/') or path.startswith('\\'):
								# Absolute path
								fullpath = path
							else:
								# Relative path
								fullpath = os.path.join(self.processes[pid].cmdhandler.current_working_dir, path)
							exitcode = self.computer.filesystem.rename_file(fullpath, str(newname, ENCODING))
			elif syscallid == 31:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Create a folder with the path given by RBX and RCX
					begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					# Get the data
					processmemory_use = self.processes[pid].get_processmemory_thread(tid)
					exitcode, foldername = processmemory_use.get_bytes(begin_offset, length)
					if exitcode != 0:
						exitcode = (exitcode, None)
					else:
						# Create the folder
						path = str(foldername, ENCODING)
						if path.startswith('/') or path.startswith('\\'):
							# Absolute path
							fullpath = path
						else:
							# Relative path
							fullpath = os.path.join(self.processes[pid].cmdhandler.current_working_dir, path)
						exitcode = self.computer.filesystem.create_directory(fullpath)
			elif syscallid == 32:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Delete a folder with the path given by RBX and RCX
					begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					# Get the data
					processmemory_use = self.processes[pid].get_processmemory_thread(tid)
					exitcode, foldername = processmemory_use.get_bytes(begin_offset, length)
					if exitcode != 0:
						exitcode = (exitcode, None)
					else:
						# Delete the folder
						path = str(foldername, ENCODING)
						if path.startswith('/') or path.startswith('\\'):
							# Absolute path
							fullpath = path
						else:
							# Relative path
							fullpath = os.path.join(self.processes[pid].cmdhandler.current_working_dir, path)
						exitcode = self.computer.filesystem.delete_directory(fullpath)
			elif syscallid == 33:
				# Return a list of the filenames in the directory given by RBX and RCX, separated by newlines and put it into the stack along with the length in RBX
				begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
				# Get the data
				processmemory_use = self.processes[pid].get_processmemory_thread(tid)
				exitcode, data = processmemory_use.get_bytes(begin_offset, length)
				if exitcode != 0:
					exitcode = (exitcode, None)
				else:
					# Read the folder
					path = str(data, ENCODING)
					if path.startswith('/') or path.startswith('\\'):
						# Absolute path
						fullpath = path
					else:
						# Relative path
						fullpath = os.path.join(self.processes[pid].cmdhandler.current_working_dir, path)
					exitcode = self.computer.filesystem.list_directory(fullpath)
					if exitcode[0] == 0:
						# Write the data in the stack
						self.processes[pid].threads[tid].stack.push(exitcode[1])
						# Modify the processes registers
						self.processes[pid].threads[tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.processes[pid].threads[tid].stack.data) + self.processes[pid].processmemory.ss, 4, byteorder='little')
						self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(exitcode[1]), 4, byteorder="little")
			elif syscallid == 34:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Run a command defined by RBX and RCX on the command line
					begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					# Get the data
					processmemory_use = self.processes[pid].get_processmemory_thread(tid)
					exitcode, data = processmemory_use.get_bytes(begin_offset, length)
					if exitcode != 0:
						exitcode = (exitcode, None)
					else:
						# Run the command
						command = str(data, ENCODING)
						exitcode = self.processes[pid].cmdhandler.handle(command)
						if exitcode[0] == 0:
							exitcode = (0, None)
			elif syscallid == 35:
				# Get the current working directory and put it into stack with the length in RBX
				data = self.processes[pid].cmdhandler.current_working_dir
				# Write the data in the stack
				self.processes[pid].threads[tid].stack.push(bytes(data, ENCODING))
				# Modify the processes registers
				self.processes[pid].threads[tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(data), 4, byteorder='little')
				self.processes[pid].threads[tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.processes[pid].threads[tid].stack.data) + self.processes[pid].processmemory.ss, 4, byteorder='little')
				exitcode = (0, None)
			elif syscallid == 36:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Format the FileSystem
					self.computer.filesystem._format()
					exitcode = (0, None)
			elif syscallid == 37:
				# Get the current time as a 8 byte integer and put it into RBX
				t = int.to_bytes(int(time.time()), 8, byteorder='little')
				self.processes[pid].threads[tid].registers['RBX'].data[0 : 8] = t
				exitcode = (0, None)
			elif syscallid == 38:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Shut down the computer
					self.computer.shutdown()
					exitcode = (0, None)
			elif syscallid == 39:
				if self.processes[pid].security_level == 1:
					exitcode = (40, "Invalid process security level.")
				else:
					# Set the password to be defined by RBX and RCX
					begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
					length = int.from_bytes(self.processes[pid].threads[tid].registers['RCX'].get_bytes(0, 4)[1], byteorder='little')
					# Get the data
					processmemory_use = self.processes[pid].get_processmemory_thread(tid)
					exitcode, data = processmemory_use.get_bytes(begin_offset, length)
					if exitcode != 0:
						exitcode = (exitcode, None)
					else:
						# Set the password
						self.computer.filesystem.password = hashlib.sha256(data).digest()
						self.computer.filesystem._backend_update()
						exitcode = (0, None)
			elif syscallid == 40:
				# Write to the processes STDOut with the beginning offset in RBX, and the end of the string indicated by a null byte
				begin_offset = int.from_bytes(self.processes[pid].threads[tid].registers['RBX'].get_bytes(0, 4)[1], byteorder='little')
				# Get the data
				processmemory_use = self.processes[pid].get_processmemory_thread(tid)
				# Get each byte
				i = begin_offset
				data = ''
				while True:
					exitcode, byte = processmemory_use.get_bytes(i, 1)
					if exitcode != 0:
						exitcode = (exitcode, None)
						break
					if byte == b'\x00':
						exitcode = (0, None)
						break
					data += str(byte, ENCODING)
					i += 1
				
				if exitcode[0] == 0:
					# Write the data to the STDOut
					exitcode = self.processes[pid].stdout.write(bytes(data, ENCODING), self.terminal)
			else:
				exitcode = (30, "Invalid SYSCall.")

			# Update memory in process
			self.update_process_memory_global(pid, tid)
			# In case of errors, set the thread's waiting state to not running/error
			self.processes[pid].threads[tid].waiting = False
			# Handle exitcode
			self.processes[pid].threads[tid].registers['RAX'].data[0 : 4] = int.to_bytes(exitcode[0], 4, byteorder='little')
		except Exception as e:
			# Handle exitcode
			self.halt_thread(pid, tid, 255)
			# Add to log
			self.log += '\n' + str(e)

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
					except Exception:
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
			# Handle exitcode
			self.processes[pid].threads[tid].registers['RAX'].data[0 : 4] = int.to_bytes(exitcode[0], 4, byteorder='little')
		except Exception as e:
			# Handle exitcode
			self.halt_thread(pid, tid, 255)

	def call_library(self, pid, tid, lid, call):

		"""Preform a dynamic library call.
		   Args: pid -> process ID of the process that called the library
		         tid -> thread ID of the thread that called the library
		         lid -> library ID to call to
		         call -> call ID to call"""

		try:
			self.processes[pid].threads[tid].waiting = True
			# Wait until the CPU has finished the thread (and registers are committed)
			while True:
				ready = True
				for cpu in self.computer.cpu.cores:
					try:
						if cpu.pname == ('proc', pid) and cpu.tid == tid:
							ready = False
					except Exception:
						pass
				if ready:
					break
			
			# Run the library call (NOTE: all library calls must call update_process_memory_global after modifying memory)
			# NOTE: All library calls must modify memory in the processes memory data, not global memory data. Using the method update_process_memory_global, memory can be synced up with all processes. 
			lid = int.from_bytes(lid, byteorder='little')
			call = int.from_bytes(call, byteorder='little')

			if lid < len(self.processes[pid].threads[tid].dynamic_libraries):
				# Get the library
				lib = self.processes[pid].threads[tid].dynamic_libraries[lid]
				if call in lib.defined_calls:
					# Call the library
					exitcode = self.processes[pid].threads[tid].dynamic_libraries[lid].handle(call)
				else:
					# Invalid call ID
					exitcode = (28, "Call ID is invalid.")
			else:
				# Invalid LID
				exitcode = (27, "Library ID is invalid.")

			# Update memory in process
			self.update_process_memory_global(pid, tid)
			# In case of errors, set the thread's waiting state to not running/error
			self.processes[pid].threads[tid].waiting = False
			# Handle exitcode
			self.processes[pid].threads[tid].registers['RAX'].data[0 : 4] = int.to_bytes(exitcode[0], 4, byteorder='little')
		except Exception as e:
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
				elif all([not self.processes[pid].threads[t].running for t in self.processes[pid].threads]):
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

		self.terminalID = None

		# Initialize all peripherals and find a terminal
		for peripheral_id, peripheral in self.computer.peripherals.items():
			peripheral.start(peripheral_id)
			# Check if the peripheral is a terminal screen
			if type(peripheral) == TerminalScreen:
				self.terminalID = peripheral_id

		if self.terminalID == None:
			raise SysError("No terminal found.")

		# Start the terminal
		self.terminal.start()

		centered_text = ' EMOS '
		num_padding = int((self.computer.peripherals[self.terminalID].cols - len(centered_text)) / 2)
		self.terminal.print_terminal(bytes('-' * self.computer.peripherals[self.terminalID].cols, ENCODING))
		self.terminal.print_terminal(b'\n')
		self.terminal.print_terminal(bytes('-' * num_padding + centered_text + '-' * num_padding, ENCODING))
		self.terminal.print_terminal(b'\n')
		self.terminal.print_terminal(bytes('-' * self.computer.peripherals[self.terminalID].cols, ENCODING))
		self.terminal.print_terminal(b'\n')

		# Authenticate the user
		if self.computer.filesystem.password:
			# Computer should have a password
			self.terminal.print_terminal(b'PASSWORD: ')
			# Get the password
			entered_password = ''
			while True:
				exitcode, char = self.terminal.get_char()
				if exitcode != 0:
					return (exitcode, char)

				if char == '\b':
					# Backspace
					if len(entered_password) == 0:
						continue
					entered_password = entered_password[ : -1]
					self.terminal.print_terminal(b'\b')
					continue
				elif char in ('\n', '\r'):
					# Newline
					self.terminal.print_terminal(b'\n')
					break

				entered_password += char
				self.terminal.print_terminal(b'*')

			# Check the password
			if hashlib.sha256(bytes(entered_password, ENCODING)).digest() == self.computer.filesystem.password:
				# Continue
				pass
			else:
				# Incorrect password
				self.terminal.print_terminal(b'INCORRECT PASSWORD')
				return (39, "Incorrect password.")

		# Start the process main loop
		self.process_mainloop()

		# Run startup files
		exitcode, data = self.computer.filesystem.read_file('/__startup.cbf')
		if exitcode != 0:
			# File cannot be loaded
			pass
		else:
			# Try to run the file
			process = self.run_executable_data(data)
			exitcode, pid = self.process_create(process)
			if exitcode == 0:
				self.terminal.set_view(pid)
				if exitcode == 0:
					# Wait for the process to finish
					self.process_await(pid)
					self.terminal.remove_view()
					# Terminate the process
					self.process_delete(pid)			

		# Try to start the command handler
		if hasattr(self, 'cmdhandler'):
			self.cmdhandler.start()

	def stop_os(self):

		"""Stop the operating system."""

		# Run shutdown files
		exitcode, data = self.computer.filesystem.read_file('/__shutdown.cbf')
		if exitcode != 0:
			# File cannot be loaded
			pass
		else:
			# Try to run the file
			process = self.run_executable_data(data)
			exitcode, pid = self.process_create(process)
			if exitcode == 0:
				self.terminal.set_view(pid)
				if exitcode == 0:
					# Wait for the process to finish
					self.process_await(pid)
					self.terminal.remove_view()
					# Terminate the process
					self.process_delete(pid)

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


class DynamicLibrary:

	"""The base class for all dynamic libraries."""

	defined_calls = []

	def __init__(self, operatingsystem, pid, tid):

		"""Create and start the dynamic library.
		   Args: operatingsystem -> the operatingsystem the dynamic library is a part of
		         pid -> the process ID the library is for
		         tid -> the thread ID the library is for"""

		self.operatingsystem = operatingsystem
		self.pid = pid
		self.tid = tid

	def end(self):

		"""Run ending protocols."""

		del self.operatingsystem
		del self.pid
		del self.tid

	def handle(self, call):

		"""Handle a call.
		   Args: call -> the call ID to run"""

		...

		# Update process memory
		self.operatingsystem.update_process_memory_global(self.pid, self.tid)
		# Exit
		return (0, None)

	def __del__(self):

		"""Delete the library."""

		self.end()

	def __repr__(self):

		"""Get the string representation of the library."""

		return "<DynamicLibrary>"

	def __str__(self):

		"""Get the string representation of the library."""

		return self.__repr__()


class ProcessCMDHandler:

	"""The main process command handler."""

	def __init__(self, current_working_dir):

		"""Create the command handler.
		   Args: current_working_dir -> the current working directory for the command handler"""

		self.current_working_dir = current_working_dir

	def initialize(self, computer):

		"""Initialize the command handler.
		   Args: computer -> the computer to use"""

		self.computer = computer

	def handle(self, command):

		"""Handle a command.
		   Args: command -> command to handle"""

		try:
			if command.lstrip() == '':
				return (0, b'')
			# Split the command
			split_command = shlex.split(command)

			# Fully split the command
			maincommand, args, pipetofile, argsfile, pipecommand = self.fully_split(split_command)

			# Get full arguments from files
			# ORDER:
			# Arguments
			# Pipe file
			# Pipe command
			if argsfile:
				for file in argsfile:
					# Read each file
					exitcode, filedata = self.computer.filesystem.read_file(os.path.join(self.current_working_dir, file) if not (file.startswith('/') or file.startswith('\\')) else file)
					if exitcode != 0:
						return (35, "Error handling command. [" + str(e) + "]")
					# Get the arguments
					args += shlex.split(str(filedata, ENCODING))

			# Add pipe command data
			if pipecommand:
				# Run the pipe command
				exitcode, stdout_data = self.handle(' '.join(pipecommand))
				if exitcode != 0:
					return (35, "Error handling command. [" + str(e) + "]")
				# Output should be a copy of the now terminated process
				args += shlex.split(str(stdout_data, ENCODING))

			enviro_dict = json.loads(str(self.computer.filesystem.read_file('./__enviro')[1], ENCODING))

			for i, arg in enumerate(args):
				if arg.startswith('%') and arg.endswith('%'):
					# Environment variable
					if arg[1 : -1] in enviro_dict:
						# Environment variable exists
						args[i] = enviro_dict[arg[1 : -1]]

			# Run the final command
			# Check if the command is a file
			directory_list = self.computer.filesystem.list_directory(self.current_working_dir)
			if directory_list[0] != 0:
				return directory_list
			directory_list = directory_list[1].split('\n')
			if 'PATH' in enviro_dict:
				enviro_path_list = shlex.split(enviro_dict['PATH'])
				for i in enviro_path_list:
					if i.endswith(maincommand + '.cbf') or i.endswith(maincommand):
						# Command is in environment variables
						maincommand = i
						break

			if (maincommand in directory_list) or (maincommand + '.cbf' in directory_list) or (self.computer.filesystem.read_file(maincommand if maincommand.startswith('/') or maincommand.startswith('\\') else os.path.join(self.current_working_dir, maincommand))[0] == 0):
				# Command is a file
				# Get full main command name
				maincommand = maincommand if maincommand.endswith('.cbf') else (maincommand + '.cbf')
				# Create the process
				file_data = self.computer.filesystem.read_file(maincommand if maincommand.startswith('/') or maincommand.startswith('\\') else os.path.join(self.current_working_dir, maincommand))
				if file_data[0] != 0:
					return file_data
				process = self.computer.operatingsystem.run_executable_data(file_data[1])
				process.security_level = self.security_level
				process.stdin.data = bytearray(b' '.join([bytes(i, ENCODING) for i in args]))
				process.cmdhandler.current_working_dir = self.current_working_dir
				exitcode, pid = self.computer.operatingsystem.process_create(process)
				if exitcode != 0:
					return (exitcode, pid)
				# Wait for the process to finish
				self.computer.operatingsystem.process_await(pid)
				# Get the processes STDOut data
				stdout_data = self.computer.operatingsystem.processes[pid].stdout.data
				# Get the processes exitcode
				exitcode = self.computer.operatingsystem.processes[pid].output[0]

				# Write the STDOut data to the pipe file
				if pipetofile:
					self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], stdout_data)

				# Terminate the process
				self.computer.operatingsystem.process_delete(pid)

				# Return with the exitcode and STDOut data
				return (exitcode, stdout_data)

			# Else, try to run a built-in command
			if maincommand == 'cd':
				# Change current working directory
				if args:
					# Change the CWD
					# Get string new path
					path = ' '.join(args)
					if not (path.startswith('/') or path.startswith('\\')):
						current = os.path.normpath(self.current_working_dir).split(os.path.sep)
						for section in os.path.normpath(path).split(os.path.sep):
							if section in ('', '.'):
								continue
							elif section == '..':
								if len(current) != 0:
									current.pop()
								else:
									return (31, "Cannot traverse back from root directory.")
							else:
								current.append(section)
						# Check if the path is valid
						newpath = '/'.join(current)
						if self.computer.filesystem.list_directory(newpath)[0] == 0:
							self.current_working_dir = newpath
						else:
							return (32, "Path is invalid.")
					else:
						# Check if the path is valid
						if self.computer.filesystem.list_directory(path)[0] == 0:
							self.current_working_dir = path
						else:
							return (32, "Path is invalid.")
					return (0, b'')
				else:
					# Get current working directory
					# Write the STDOut data to the pipe file
					if pipetofile:
						return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(self.current_working_dir, ENCODING))[0], bytes(self.current_working_dir, ENCODING))
					return (0, bytes(self.current_working_dir, ENCODING))
			elif maincommand == 'ldir':
				# List the current directory, separated by newlines
				# Get full path
				if args:
					if args[0].startswith('/') or args[0].startswith('\\'):
						# Absolute
						fullpath = args[0]
					else:
						# Relative
						fullpath = os.path.join(self.current_working_dir, args[0])
				else:
					fullpath = self.current_working_dir

				exitcode = self.computer.filesystem.list_directory(fullpath)
				if exitcode[0] != 0:
					return exitcode

				listdir = exitcode[1]

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(listdir, ENCODING))[0], bytes(listdir, ENCODING))
				return (0, bytes(listdir, ENCODING))
			elif maincommand == 'echo':
				# Echo the arguments
				data = ' '.join(args)

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
				return (0, bytes(data, ENCODING))
			elif maincommand == 'del':
				# Delete a file or folder
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])

				# Delete the path
				exitcode, exitphrase = self.computer.filesystem.delete_file(fullpath)
				if exitcode == 32:
					return (self.computer.filesystem.delete_directory(fullpath)[0], b'')
				else:
					return (exitcode, b'')

			elif maincommand == 'rname':
				# Rename a file or folder
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])

				# Rename the path
				return (self.computer.filesystem.rename_file(fullpath, args[1])[0], b'')

			elif maincommand == 'mkdir':
				# Create a folder
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])

				# Create the path
				return (self.computer.filesystem.create_directory(fullpath)[0], b'')

			elif maincommand == 'compile':
				# Compile a file
				try:
					# Get full path
					if args[0].startswith('/') or args[0].startswith('\\'):
						# Absolute
						fullpath = args[0]
					else:
						# Relative
						fullpath = os.path.join(self.current_working_dir, args[0])
						
					# Get the file
					exitcode = self.computer.filesystem.read_file(fullpath)
					if exitcode[0] != 0:
						return exitcode
					codefile = str(exitcode[1], ENCODING)

					# Parse and compile the code
					parser = parse.Compiler(codefile, 'emos', self.computer.operatingsystem, self.current_working_dir)
					parser.parse()
					parser.compile()

					compiled = parser.compiled
					linked = bytearray(int.to_bytes((parser.data_index if parser.data_index else len(parser.compiled)), 4, byteorder='little')) + compiled

					# Write the code to the file
					# Get full path
					if args[1].startswith('/') or args[1].startswith('\\'):
						# Absolute
						fullpath = args[1]
					else:
						# Relative
						fullpath = os.path.join(self.current_working_dir, args[1])
					return (self.computer.filesystem.write_file(fullpath, linked)[0], b'')
				except Exception as e:
					# Error
					self.computer.operatingsystem.log += (str(e) + '\n')
					return (37, "Parse error. [" + str(e) + "]")

			elif maincommand == 'time':
				# Get the current time
				data = time.asctime()

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
				return (0, bytes(data, ENCODING))

			elif maincommand == 'shutdown':
				# Shut down the computer
				self.computer.shutdown()

			elif maincommand == 'clear':
				# Clear the screen
				self.computer.operatingsystem.terminal.clear()

				return (0, b'')

			elif maincommand == 'read':
				# Read a file
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
						
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				data = str(exitcode[1], ENCODING)

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
				return (0, bytes(data, ENCODING))

			elif maincommand == 'run':
				# Run a shell script
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
					
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				codefile = str(exitcode[1], ENCODING)

				# Split the code file
				code_split = codefile.split('\n')
				# Run each command
				for command in code_split:
					exitcode, output = self.handle(command)
					if exitcode != 0:
						return (exitcode, output)

				return (0, b'')

			elif maincommand == 'sec':
				# Set the security level
				self.security_level = int(args[0])

			elif maincommand == 'copy':
				# Copy a file to a different file
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
					
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				filedata = exitcode[1]

				# Write to the second file
				if args[1].startswith('/') or args[1].startswith('\\'):
					# Absolute
					fullpath = args[1]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[1])
					
				# Write to the file
				return (self.computer.filesystem.write_file(fullpath, filedata)[0], b'')

			elif maincommand == 'env':
				# Modify or get environment variables
				env_command = args.pop(0)

				env_data = json.loads(str(self.computer.filesystem.read_file('./__enviro')[1], ENCODING))

				if env_command == 'get':
					# Get an environment variable
					if args[0] not in env_data:
						return (42, "Invalid environment variable name.")
					data = env_data[args[0]]

					if pipetofile:
						return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
					return (0, bytes(data, ENCODING))
				elif env_command == 'set':
					# Set an environment variable+
					var_name = args.pop(0)
					# Get the data
					data = ' '.join(args)
					# Put the data into the environment file
					env_data[var_name] = data
					# Write the file back
					return (self.computer.filesystem.write_file('./__enviro', bytes(json.dumps(env_data), ENCODING))[0], b'')
				elif env_command == 'del':
					# Delete an environment variable
					var_name = args.pop(0)
					del env_data[var_name]
					# Write the file back
					return (self.computer.filesystem.write_file('./__enviro', bytes(json.dumps(env_data), ENCODING))[0], b'')

			elif maincommand == 'move':
				# Move a file in the filesystem
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
					
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				filedata = exitcode[1]

				# Delete the file
				exitcode = self.computer.filesystem.delete_file(fullpath)
				if exitcode[0] != 0:
					return exitcode

				# Write to the second file
				if args[1].startswith('/') or args[1].startswith('\\'):
					# Absolute
					fullpath = args[1]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[1])
					
				# Write to the file
				return (self.computer.filesystem.write_file(fullpath, filedata)[0], b'')

			return (36, "Illegal command.")

		except Exception as e:
			# Error
			self.computer.operatingsystem.log += (str(e) + '\n')

			return (35, "Error handling command. [" + str(e) + "]")

	def fully_split(self, split_command):

		"""Fully split a command into the main command, arguments, pipe file, argument file, and pipe command.
		   Args: split_command -> the already split command (using shlex)"""

		# Find different sections of the command
		fully_split_command = [[], [], [], []]
		current_state = ''
		for section in split_command:
			if section in ('>', '<', '|'):
				current_state = section
				continue

			if current_state == '':
				fully_split_command[0].append(section)
			elif current_state == '>':
				fully_split_command[1].append(section)
			elif current_state == '<':
				fully_split_command[2].append(section)
			elif current_state == '|':
				fully_split_command[3].append(section)

		maincommand, args = fully_split_command[0][0], fully_split_command[0][1 : ]
		pipetofile = fully_split_command[1]
		argsfile = fully_split_command[2]
		pipecommand = fully_split_command[3]

		return maincommand, args, pipetofile, argsfile, pipecommand


class CMDHandler:

	"""The main command handler."""

	# Command help sheet
	COMMANDS_HELP = {
		'cd' : 'Change the directory or get the current directory.',
		'ldir' : 'List the contents of the current directory or any other directory.',
		'echo' : 'Echo back the arguments.',
		'del' : 'Delete a file or folder.',
		'rname' : 'Rename a file or folder.',
		'mkdir' : 'Create a new directory.',
		'compile' : 'Compile and link EMOS code.',
		'time' : 'Get the current time.',
		'shutdown' : 'Shut down the computer.',
		'clear' : 'Clear the screen',
		'read' : 'Read a file from the computer.',
		'edit' : 'Edit a file to the computer.',
		'help' : 'Get help.'
	}

	def __init__(self, current_working_dir, security_level=0):

		"""Create the command handler.
		   Args: current_working_dir -> the current working directory for the command handler"""

		self.current_working_dir = current_working_dir

		self.security_level = security_level

	def initialize(self, computer):

		"""Initialize the command handler.
		   Args: computer -> the computer to use"""

		self.computer = computer
		self.terminal = self.computer.operatingsystem.terminal
		self.stealable = True

	def start(self):

		"""Start the command line."""

		self.running = True
		threading.Thread(target=self._start).start()

	def _start(self):

		"""Start the command line (backend)."""

		while self.running:
			try:
				self.stealable = False
				# Print the prompt
				self.terminal.print_terminal(bytes('EMOS | ' + self.current_working_dir + '>', ENCODING))

				# Take input
				exitcode, input_data = self.terminal.get_input()
				self.terminal.print_terminal(b'\n')
				if exitcode != 0:
					self.terminal.print_terminal(bytes('ERROR: ' + str(exitcode) + ' - ' + input_data))
					continue

				# Run the command
				exitcode, data = self.handle(input_data)

				if exitcode != 0:
					self.terminal.print_terminal(bytes('ERROR: ' + str(exitcode) + ' - ' + str(data), ENCODING))
				else:
					self.terminal.print_terminal(data)

				self.terminal.print_terminal(b'\n')

			except Exception as e:
				# Find a shut down error
				self.running = False
				self.stealable = True

	def handle(self, command):

		"""Handle a command.
		   Args: command -> command to handle"""

		try:
			if command.lstrip() == '':
				return (0, b'')

			# Split the command
			split_command = shlex.split(command)

			# Fully split the command
			maincommand, args, pipetofile, argsfile, pipecommand = self.fully_split(split_command)

			# Get full arguments from files
			# ORDER:
			# Arguments
			# Pipe file
			# Pipe command
			if argsfile:
				for file in argsfile:
					# Read each file
					exitcode, filedata = self.computer.filesystem.read_file(os.path.join(self.current_working_dir, file) if not (file.startswith('/') or file.startswith('\\')) else file)
					if exitcode != 0:
						return (35, "Error handling command. [" + str(e) + "]")
					# Get the arguments
					args += shlex.split(str(filedata, ENCODING))

			# Add pipe command data
			if pipecommand:
				# Run the pipe command
				exitcode, stdout_data = self.handle(' '.join(pipecommand))
				if exitcode != 0:
					return (35, "Error handling command. [" + str(e) + "]")
				# Output should be a copy of the now terminated process
				args += shlex.split(str(stdout_data, ENCODING))

			enviro_dict = json.loads(str(self.computer.filesystem.read_file('./__enviro')[1], ENCODING))

			for i, arg in enumerate(args):
				if arg.startswith('%') and arg.endswith('%'):
					# Environment variable
					if arg[1 : -1] in enviro_dict:
						# Environment variable exists
						args[i] = enviro_dict[arg[1 : -1]]

			# Run the final command
			# Check if the command is a file
			directory_list = self.computer.filesystem.list_directory(self.current_working_dir)
			if directory_list[0] != 0:
				return directory_list
			directory_list = directory_list[1].split('\n')
			if 'PATH' in enviro_dict:
				enviro_path_list = shlex.split(enviro_dict['PATH'])
				for i in enviro_path_list:
					if i.endswith(maincommand + '.cbf') or i.endswith(maincommand):
						# Command is in environment variables
						maincommand = i
						break

			if (maincommand in directory_list) or (maincommand + '.cbf' in directory_list) or (self.computer.filesystem.read_file(maincommand if maincommand.startswith('/') or maincommand.startswith('\\') else os.path.join(self.current_working_dir, maincommand))[0] == 0):
				# Command is a file
				# Get full main command name
				maincommand = maincommand if maincommand.endswith('.cbf') else (maincommand + '.cbf')
				# Create the process
				file_data = self.computer.filesystem.read_file(maincommand if maincommand.startswith('/') or maincommand.startswith('\\') else os.path.join(self.current_working_dir, maincommand))
				if file_data[0] != 0:
					return file_data
				process = self.computer.operatingsystem.run_executable_data(file_data[1])
				process.security_level = self.security_level
				process.stdin.data = bytearray(b' '.join([bytes(i, ENCODING) for i in args]))
				process.cmdhandler.current_working_dir = self.current_working_dir
				self.stealable = True
				exitcode, pid = self.computer.operatingsystem.process_create(process)
				self.terminal.set_view(pid)
				if exitcode != 0:
					return (exitcode, pid)
				# Wait for the process to finish
				self.computer.operatingsystem.process_await(pid)
				self.terminal.remove_view()
				self.stealable = False
				# Get the processes exitcode
				exitcode, exitphrase = self.computer.operatingsystem.processes[pid].output
				# Get the processes STDOut
				stdout_data = self.computer.operatingsystem.processes[pid].stdout.data

				# Write the STDOut data to the pipe file
				if pipetofile:
					self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], stdout_data)

				# Terminate the process
				self.computer.operatingsystem.process_delete(pid)

				# Return with the exitcode and STDOut data
				if exitcode != 0:
					return (exitcode, exitphrase)
				return (exitcode, b'')

			# Else, try to run a built-in command
			if maincommand == 'cd':
				# Change current working directory
				if args:
					# Change the CWD
					# Get string new path
					path = ' '.join(args)
					if not (path.startswith('/') or path.startswith('\\')):
						current = os.path.normpath(self.current_working_dir).split(os.path.sep)
						for section in os.path.normpath(path).split(os.path.sep):
							if section in ('', '.'):
								continue
							elif section == '..':
								if len(current) != 0:
									current.pop()
								else:
									return (31, "Cannot traverse back from root directory.")
							else:
								current.append(section)
						# Check if the path is valid
						newpath = '/'.join(current)
						if self.computer.filesystem.list_directory(newpath)[0] == 0:
							self.current_working_dir = newpath
						else:
							return (32, "Path is invalid.")
					else:
						# Check if the path is valid
						if self.computer.filesystem.list_directory(path)[0] == 0:
							self.current_working_dir = path
						else:
							return (32, "Path is invalid.")
					return (0, b'')
				else:
					# Get current working directory
					# Write the STDOut data to the pipe file
					if pipetofile:
						return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(self.current_working_dir, ENCODING))[0], bytes(self.current_working_dir, ENCODING))
					return (0, bytes(self.current_working_dir, ENCODING))
			elif maincommand == 'ldir':
				# List the current directory, separated by newlines
				# Get full path
				if args:
					if args[0].startswith('/') or args[0].startswith('\\'):
						# Absolute
						fullpath = args[0]
					else:
						# Relative
						fullpath = os.path.join(self.current_working_dir, args[0])
				else:
					fullpath = self.current_working_dir

				exitcode = self.computer.filesystem.list_directory(fullpath)
				if exitcode[0] != 0:
					return exitcode

				listdir = exitcode[1]

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(listdir, ENCODING))[0], bytes(listdir, ENCODING))
				
				return (0, bytes(listdir, ENCODING))
			elif maincommand == 'echo':
				# Echo the arguments
				data = ' '.join(args)

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
				return (0, bytes(data, ENCODING))
			elif maincommand == 'del':
				# Delete a file or folder
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])

				# Delete the path
				exitcode, exitphrase = self.computer.filesystem.delete_file(fullpath)
				if exitcode == 32:
					return (self.computer.filesystem.delete_directory(fullpath)[0], b'')
				else:
					return (exitcode, b'')

			elif maincommand == 'rname':
				# Rename a file or folder
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])

				# Rename the path
				return (self.computer.filesystem.rename_file(fullpath, args[1])[0], b'')

			elif maincommand == 'mkdir':
				# Create a folder
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])

				# Create the path
				return (self.computer.filesystem.create_directory(fullpath)[0], b'')

			elif maincommand == 'compile':
				# Compile a file
				try:
					# Get full path
					if args[0].startswith('/') or args[0].startswith('\\'):
						# Absolute
						fullpath = args[0]
					else:
						# Relative
						fullpath = os.path.join(self.current_working_dir, args[0])
						
					# Get the file
					exitcode = self.computer.filesystem.read_file(fullpath)
					if exitcode[0] != 0:
						return exitcode
					codefile = str(exitcode[1], ENCODING)

					# Parse and compile the code
					parser = parse.Compiler(codefile, 'emos', self.computer.operatingsystem, self.current_working_dir)
					parser.parse()
					parser.compile()

					compiled = parser.compiled
					linked = bytearray(int.to_bytes((parser.data_index if parser.data_index else len(parser.compiled)), 4, byteorder='little')) + compiled

					# Write the code to the file
					# Get full path
					if args[1].startswith('/') or args[1].startswith('\\'):
						# Absolute
						fullpath = args[1]
					else:
						# Relative
						fullpath = os.path.join(self.current_working_dir, args[1])
					return (self.computer.filesystem.write_file(fullpath, linked)[0], b'')
				except Exception as e:
					# Error
					self.computer.operatingsystem.log += (str(e) + '\n')
					return (37, "Parse error. [" + str(e) + "]")

			elif maincommand == 'time':
				# Get the current time
				data = time.asctime()

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
				return (0, bytes(data, ENCODING))

			elif maincommand == 'shutdown':
				# Shut down the computer
				self.stealable = True
				self.computer.shutdown()

			elif maincommand == 'clear':
				# Clear the screen
				self.terminal.clear()

				return (0, b'')

			elif maincommand == 'read':
				# Read a file
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
						
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				data = str(exitcode[1], ENCODING)

				# Get the number of lines
				if len(args) == 2:
					# Get length attribute
					lines = int(args[1])
					data = '\n'.join(data.split('\n')[ : lines])

				if pipetofile:
					return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
				return (0, bytes(data, ENCODING))

			elif maincommand == 'edit':
				# Edit a multi-line file
				editor = WRITELIB(self.computer.operatingsystem, None, None)
				data = editor.editor()

				self.terminal.print_terminal(b"Save (y/n)? ")
				exitcode, save_yn = self.terminal.get_input()
				if exitcode != 0:
					return (exitcode, save_yn)
				save_yn = save_yn[0].upper()

				if save_yn == 'N':
					return (0, b'')

				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
						
				# Write to the file
				return (self.computer.filesystem.write_file(fullpath, data)[0], b'')

			elif maincommand == 'help':
				# Get help with a command or get a description of all commands
				if args:
					# Get help with a certain command
					return (0, bytes(self.COMMANDS_HELP[args[0]] if args[0] in self.COMMANDS_HELP else 'The command does not exist.', ENCODING))
				# Get all commands
				text = ''
				for name in self.COMMANDS_HELP:
					text += name.upper() + ': ' + self.COMMANDS_HELP[name] + '\n'

				return (0, bytes(text, ENCODING))

			elif maincommand == 'run':
				# Run a shell script
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
					
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				codefile = str(exitcode[1], ENCODING)

				# Split the code file
				code_split = codefile.split('\n')
				# Run each command
				for command in code_split:
					exitcode, output = self.handle(command)
					if exitcode != 0:
						return (exitcode, output)
					else:
						self.terminal.print_terminal(output + b'\n')

				return (0, b'')

			elif maincommand == 'sec':
				# Set the security level
				self.security_level = int(args[0])

				return (0, b'')

			elif maincommand == 'copy':
				# Copy a file to a different file
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
					
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				filedata = exitcode[1]

				# Write to the second file
				if args[1].startswith('/') or args[1].startswith('\\'):
					# Absolute
					fullpath = args[1]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[1])
					
				# Write to the file
				return (self.computer.filesystem.write_file(fullpath, filedata)[0], b'')

			elif maincommand == 'env':
				# Modify or get environment variables
				env_command = args.pop(0)

				env_data = json.loads(str(self.computer.filesystem.read_file('./__enviro')[1], ENCODING))

				if env_command == 'get':
					# Get an environment variable
					if args[0] not in env_data:
						return (42, "Invalid environment variable name.")
					data = env_data[args[0]]

					if pipetofile:
						return (self.computer.filesystem.write_file(os.path.join(self.current_working_dir, pipetofile[0]) if not (pipetofile[0].startswith('/') or pipetofile[0].startswith('\\')) else pipetofile[0], bytes(data, ENCODING))[0], bytes(data, ENCODING))
					return (0, bytes(data, ENCODING))
				elif env_command == 'set':
					# Set an environment variable
					var_name = args.pop(0)
					# Get the data
					data = ' '.join(args)
					# Put the data into the environment file
					env_data[var_name] = data
					# Write the file back
					return (self.computer.filesystem.write_file('./__enviro', bytes(json.dumps(env_data), ENCODING))[0], b'')
				elif env_command == 'del':
					# Delete an environment variable
					var_name = args.pop(0)
					del env_data[var_name]
					# Write the file back
					return (self.computer.filesystem.write_file('./__enviro', bytes(json.dumps(env_data), ENCODING))[0], b'')

			elif maincommand == 'move':
				# Move a file in the filesystem
				# Get full path
				if args[0].startswith('/') or args[0].startswith('\\'):
					# Absolute
					fullpath = args[0]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[0])
					
				# Get the file
				exitcode = self.computer.filesystem.read_file(fullpath)
				if exitcode[0] != 0:
					return exitcode
				filedata = exitcode[1]

				# Delete the file
				exitcode = self.computer.filesystem.delete_file(fullpath)
				if exitcode[0] != 0:
					return exitcode

				# Write to the second file
				if args[1].startswith('/') or args[1].startswith('\\'):
					# Absolute
					fullpath = args[1]
				else:
					# Relative
					fullpath = os.path.join(self.current_working_dir, args[1])
					
				# Write to the file
				return (self.computer.filesystem.write_file(fullpath, filedata)[0], b'')

			return (36, "Illegal command.")

		except Exception as e:
			# Error
			self.computer.operatingsystem.log += (str(e) + '\n')

			return (35, "Error handling command. [" + str(e) + "]")

	def fully_split(self, split_command):

		"""Fully split a command into the main command, arguments, pipe file, argument file, and pipe command.
		   Args: split_command -> the already split command (using shlex)"""

		# Find different sections of the command
		fully_split_command = [[], [], [], []]
		current_state = ''
		for section in split_command:
			if section in ('>', '<', '|'):
				current_state = section
				continue

			if current_state == '':
				fully_split_command[0].append(section)
			elif current_state == '>':
				fully_split_command[1].append(section)
			elif current_state == '<':
				fully_split_command[2].append(section)
			elif current_state == '|':
				fully_split_command[3].append(section)

		maincommand, args = fully_split_command[0][0], fully_split_command[0][1 : ]
		pipetofile = fully_split_command[1]
		argsfile = fully_split_command[2]
		pipecommand = fully_split_command[3]

		return maincommand, args, pipetofile, argsfile, pipecommand


class Process:

	"""The main process object."""

	def __init__(self, processmemory, threads, state, security_level=0):

		"""Create the process.
		   Args: processmemory -> the process memory for the process
		         threads -> a dictionary containing all the thread ids and the threads
		         state -> string containing the state of the process. 'r' for running, or 't' for terminated/stopped/error
		         secutiry_level -> the security level which the process is at. 0 for full access, and 1 for limited access"""

		self.processmemory = processmemory
		self.threads = threads
		self.state = state

		self.stdout = STDOut()
		self.stdin = STDIn()

		self.open_files = []

		self.cmdhandler = ProcessCMDHandler('')

		self.security_level = security_level

	def get_processmemory_thread(self, tid):

		"""Get the process memory for a specific thread.
		   Args: tid -> the thread id"""

		stack = self.threads[tid].stack
		newpm = copy.deepcopy(self.processmemory)
		newpm.stack = stack
		newpm.es = newpm.ss + len(newpm.stack.data)

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

	def initialize(self, computer):

		"""Initialize the process.
		   Args: computer -> the computer to initialize with"""

		self.computer = computer
		self.cmdhandler.initialize(self.computer)

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

		self.dynamic_libraries = []

	def __repr__(self):

		"""Get the string representation of the process."""

		return "<PThread TID " + str(self.tid) + " running" * self.running + ">"

	def __str__(self):

		"""Get the string representation of the process."""

		return self.__repr__()


class Terminal:

	"""The base class for a terminal or console display."""

	def __init__(self, computer):

		"""Create the terminal.
		   Args: computer -> the computer the terminal is attached to"""

		self.computer = computer

		self.state = 'term'
		self.data = bytearray()

	def start(self):

		"""Start the terminal."""

		self.operatingsystem = self.computer.operatingsystem
		self.terminalID = self.computer.operatingsystem.terminalID

	def set_view(self, pid):

		"""Set the display to view a specific PID's STDOut.
		   Args: pid -> process ID to view"""

		if pid not in self.operatingsystem.processes:
			return (20, "PID doesn't exist.")

		# Check if a CMDHandler exists, and if so, if it is ready
		if hasattr(self.operatingsystem, 'cmdhandler'):
			if not self.operatingsystem.cmdhandler.stealable:
				return (38, "Command handler is not ready to be stolen.")

		self.pid_view = pid
		self.stdout = self.operatingsystem.processes[pid].stdout
		self.stdin = self.operatingsystem.processes[pid].stdin
		self.stdout.active = True
		self.stdin.active = True
		
		self.state = 'proc'

		self.notify_change()

		return (0, None)

	def kernel_mode(self):

		"""Set the display to view the kernel's STDOut."""

		self.pid_view = None
		self.stdout = self.operatingsystem.kernel_stdout
		self.stdin = None
		self.stdout.active = True

		self.state = 'kern'

		self.notify_change()

		return (0, None)

	def remove_view(self):

		"""Unset the display view from any PID's STDOut."""

		# Add the final STDOut data to our data permanently
		self.data += self.stdout.data

		self.stdout.active = False
		if self.stdin != None:
			self.stdin.active = False

		del self.pid_view
		del self.stdout
		del self.stdin

		self.state = 'term'

		self.notify_change()

		return (0, None)

	def notify_change(self):

		"""Notify that the STDOut changed and update the terminal screen."""

		size_x = self.computer.peripherals[self.terminalID].cols
		size_y = self.computer.peripherals[self.terminalID].rows

		# Check for terminal or output mode
		if self.state == 'term':
			# Cut the data, and then write the data
			# Cut the data
			self.data = self.data[-(size_x * size_y + size_y) : ]
			# Write the data
			self.computer.memory.memorypartitions[('perp', self.terminalID)].set_data(self.data + bytes((size_x * size_y + size_y) - len(self.data)))
			self.computer.peripherals[self.terminalID].update_screen()
		elif self.state == 'proc':
			# Write the data with the STDOut data and cut it too
			# Add the STDOut data and cut the data
			data = self.data + self.stdout.pipe()[1]
			# Cut the data
			data = data[-(size_x * size_y + size_y) : ]
			# Write the data
			self.computer.memory.memorypartitions[('perp', self.terminalID)].set_data(data + bytes((size_x * size_y + size_y) - len(data)))
			self.computer.peripherals[self.terminalID].update_screen()
		elif self.state == 'kern':
			# Write the kernel STDOut to the screen
			data = self.stdout.pipe()[1]
			# Cut the data
			data = data[-(size_x * size_y + size_y) : ]
			# Write the data
			self.computer.memory.memorypartitions[('perp', self.terminalID)].set_data(data + bytes((size_x * size_y + size_y) - len(data)))
			self.computer.peripherals[self.terminalID].update_screen()

		return (0, None)

	def clear(self):

		"""Clear the terminal window."""

		self.data = b''

		if self.state in ('proc', 'kern'):
			self.stdout.data = b''

		self.notify_change()

	def get_char(self):

		"""Get one character from the terminal, without echoing."""

		return (0, getchars(1))

	def get_chars(self, n):

		"""Get N characters from the terminal, without echoing.
		   Args: n -> number of chars to get"""

		return (0, getchars(n))

	def get_input(self):

		"""Get input from the terminal, with echoing."""

		# Check the state
		if self.state in ('term', 'kern'):
			# Get the standard input
			input_data = input()
			self.print_terminal(bytes(input_data, ENCODING))
			return (0, input_data)

		text = ""
		# Iterate over each character in the input
		while True:
			# Get a character
			char = getchars(1)
			# Add the character
			orig_text = text
			if char == '\b':
				text = text[ : -1]
			elif char in ('\r', '\n'):
				break
			else:
				text += char
			# Print the character
			if not (len(orig_text) == 0 and char == '\b'):
				self.stdout.write(bytes(char, ENCODING), self)

		return (0, text)

	def print_terminal(self, data):

		"""Print to the terminal."""

		# Add each character, handling backspaces
		for char in data:
			# Check for a backspace
			if bytes([char]) == b'\b':
				# Delete the last char
				self.data = self.data[ : -1]
			else:
				# Add the char
				self.data += bytes([char])

		if self.state in ('term', 'kern'):
			self.notify_change()

		return (0, None)

	def __repr__(self):

		"""Get the string representation of the terminal."""

		return "<Terminal>"

	def __str__(self):

		"""Get the string representation of the terminal."""

		return self.__repr__()


class STDOut:

	"""The basic standard output class. Each process gets a standard output handle. The output gets mapped into the terminal/console."""

	def __init__(self):

		"""Create the standard output."""

		self.data = bytearray()
		self.active = False

	def write(self, data, terminal):

		"""Write data into the output stream, and notify the attached terminal.
		   Args: data -> data to add
		         terminal -> terminal to notify"""

		# Add each character, handling backspaces
		for char in data:
			# Check for a backspace
			if bytes([char]) == b'\b':
				# Delete the last char
				self.data = self.data[ : -1]
			else:
				# Add the char
				self.data += bytes([char])

		if self.active:
			# Notify the terminal
			terminal.notify_change()

		return (0, None)

	def set_data(self, data, terminal):

		"""Set data for the output stream, and notify the attached terminal.
		   Args: data -> data to add
		         terminal -> terminal to notify"""

		self.data = bytearray()

		# Add each character, handling backspaces
		for char in data:
			# Check for a backspace
			if bytes([char]) == b'\b':
				# Delete the last char
				self.data = self.data[ : -1]
			else:
				# Add the char
				self.data += bytes([char])

		if self.active:
			# Notify the terminal
			terminal.notify_change()

		return (0, None)

	def pipe(self):

		"""Pipe/return the output stream."""

		return (0, self.data)

	def __repr__(self):

		"""Get the string representation of the STDOut."""

		return "<STDOut>"

	def __str__(self):

		"""Get the string representation of the STDOut."""

		return self.__repr__()


class STDIn:

	"""The basic standard input class."""

	def __init__(self):

		"""Create the standard input."""

		self.active = False
		self.data = bytearray()

	def read(self, terminal):

		"""Read from a terminal.
		   Args: terminal -> terminal to read from"""

		if self.active:
			if len(self.data) == 0:
				return terminal.get_char()
			else:
				return (0, chr(self.data.pop(0)))
		else:
			if len(self.data) == 0:
				return (24, "STDIn not attached to a terminal.")
			else:
				return (0, chr(self.data.pop(0)))

	def readn(self, n, terminal):

		"""Read N characters from a terminal.
		   Args: n -> number of characters to read
		   		 terminal -> terminal to read from"""

		if self.active:
			final_text = ''
			for i in range(n):
				exitcode, char = self.read(terminal)
				if exitcode != 0:
					return (exitcode, char)
				final_text += char
			return (0, final_text)
		else:
			if len(self.data) == 0:
				return (24, "STDIn not attached to a terminal.")
			else:
				final_text = ''
				for i in range(n):
					exitcode, char = self.read(terminal)
					if exitcode != 0:
						return (exitcode, char)
					final_text += char
				return (0, final_text)

	def take_input(self, terminal):

		"""Take input from a terminal, echoing back.
		   Args: terminal -> terminal to take input from"""

		if self.active:
			return terminal.get_input()
		else:
			return (24, "STDIn not attached to a terminal.")

	def __repr__(self):

		"""Get the string representation of the STDIn."""

		return "<STDIn>"

	def __str__(self):

		"""Get the string representation of the STDIn."""

		return self.__repr__()


class INT_STR_LIB(DynamicLibrary):

	defined_calls = [0, 1, 2, 3]

	"""Integer and string conversion library."""

	def handle(self, call):

		"""Handle a call.
		   Args: call -> the call ID to run"""

		if call == 0:
			# Take an integer value from R9, convert it into a decimal string, and put the string into the stack, along with the length of the string in RBX
			value = int.from_bytes(self.operatingsystem.processes[self.pid].threads[self.tid].registers['R9'].data[0 : 4], byteorder='little')
			# Get the string representation
			str_value = bytes(str(value), ENCODING)
			# Place the string into the stack
			self.operatingsystem.processes[self.pid].threads[self.tid].stack.push(str_value)
			# Modify the processes registers
			self.operatingsystem.processes[self.pid].threads[self.tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.operatingsystem.processes[self.pid].threads[self.tid].stack.data) + self.operatingsystem.processes[self.pid].processmemory.ss, 4, byteorder='little')
			self.operatingsystem.processes[self.pid].threads[self.tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(str_value), 4, byteorder='little')
			# Exit code
			exitcode = (0, None)
		elif call == 1:
			# Take a string (offset in R9 and length in R10) and put it's integer representation into RBX
			offset = int.from_bytes(self.operatingsystem.processes[self.pid].threads[self.tid].registers['R9'].data[0 : 4], byteorder='little')
			length = int.from_bytes(self.operatingsystem.processes[self.pid].threads[self.tid].registers['R10'].data[0 : 4], byteorder='little')
			# Get data
			processmemory_use = self.operatingsystem.processes[self.pid].get_processmemory_thread(self.tid)
			exitcode, data = processmemory_use.get_bytes(offset, length)
			if exitcode != 0:
				exitcode = (exitcode, None)
			else:
				# Write the data to the STDOut
				int_value = int(str(data, ENCODING))
				self.operatingsystem.processes[self.pid].threads[self.tid].registers['RBX'].data[0 : 4] = int.to_bytes(int_value, 4, byteorder='little')
				exitcode = (0, None)
		elif call == 2:
			# Take an signed integer value from R9, convert it into a decimal string, and put the string into the stack, along with the length of the string in RBX
			value = int.from_bytes(self.operatingsystem.processes[self.pid].threads[self.tid].registers['R9'].data[0 : 4], byteorder='little', signed=True)
			# Get the string representation
			str_value = bytes(str(value), ENCODING)
			# Place the string into the stack
			self.operatingsystem.processes[self.pid].threads[self.tid].stack.push(str_value)
			# Modify the processes registers
			self.operatingsystem.processes[self.pid].threads[self.tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.operatingsystem.processes[self.pid].threads[self.tid].stack.data) + self.operatingsystem.processes[self.pid].processmemory.ss, 4, byteorder='little')
			self.operatingsystem.processes[self.pid].threads[self.tid].registers['RBX'].data[0 : 4] = int.to_bytes(len(str_value), 4, byteorder='little')
			# Exit code
			exitcode = (0, None)
		elif call == 3:
			# Take a string (offset in R9 and length in R10) and put it's signed integer representation into RBX
			offset = int.from_bytes(self.operatingsystem.processes[self.pid].threads[self.tid].registers['R9'].data[0 : 4], byteorder='little')
			length = int.from_bytes(self.operatingsystem.processes[self.pid].threads[self.tid].registers['R10'].data[0 : 4], byteorder='little')
			# Get data
			processmemory_use = self.operatingsystem.processes[self.pid].get_processmemory_thread(self.tid)
			exitcode, data = processmemory_use.get_bytes(offset, length)
			if exitcode != 0:
				exitcode = (exitcode, None)
			else:
				# Write the data to the STDOut
				int_value = int(str(data, ENCODING))
				self.operatingsystem.processes[self.pid].threads[self.tid].registers['RBX'].data[0 : 4] = int.to_bytes(int_value, 4, byteorder='little', signed=True)
				exitcode = (0, None)

		self.operatingsystem.update_process_memory_global(self.pid, self.tid)
		return exitcode


class WRITELIB(DynamicLibrary):

	defined_calls = [0]

	"""Writing editor library."""

	def handle(self, call):

		"""Handle a call.
		   Args: call -> the call ID to run"""

		if call == 0:
			# Use a simple editor to get data and put it into heap
			data = self.editor()
			# Create a heap memory portion
			exitcode, heap_id = self.operatingsystem.allocate_memory()
			if exitcode != 0:
				exitcode = (exitcode, None)
			else:
				exitcode = self.operatingsystem.edit_memory(heap_id, data, 0)

		self.operatingsystem.update_process_memory_global(self.pid, self.tid)
		return exitcode

	def editor(self):

		"""Take input in lines, stopping at a Ctrl-G, and return the data."""

		data = b''
		# Continually get data
		while True:
			# Get a line of data
			data += bytes(self.operatingsystem.terminal.get_input()[1], ENCODING)
			# Check for a Ctrl-G
			if len(data) > 0 and data[-1] == 7:
				# Stop
				data = data[ : -1]
				break
			# Print a newline
			if self.operatingsystem.terminal.state in ('proc', 'kern'):
				self.operatingsystem.terminal.stdout.write(b'\n', self.operatingsystem.terminal)
			else:
				self.operatingsystem.terminal.print_terminal(b'\n')
			data += b'\n'

		# Return the data
		return data
