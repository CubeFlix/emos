class TerminalScreen(Peripheral):

	"""The terminal screen class."""

	defined_interrupts = [0xe0, 0xe1, 0xe2]

	def __init__(self, computer):

		"""Create the terminal."""

		self.computer = computer

	def start(self, pid):

		"""Run starting or initialization protocols.
		   Args: pid -> peripheral ID"""

		self.pid = pid

		# Get screen size
		size = os.get_terminal_size()
		self.rows = size.lines
		self.cols = size.columns
		
		# Create the designated memory for the terminal's printout
		self.computer.memory.add_memory_partition(('perp', self.pid), MemorySection('terminal_perp_' + str(self.pid), self.rows * self.cols, b' ' * self.rows * self.cols))

		# Define the cursor pos
		self.cursor_pos_x = 0
		self.cursor_pos_y = 0

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
			self.update_cursor_pos()
			return self.update_screen()
		elif iid == 0xe1:
			# Get one char and save it to RAX
			char = getchars(1)
			self.update_cursor_pos()
			# Place the char in RAX
			self.computer.operatingsystem.processes[pid].threads[tid].registers['RAX'].data[0] = ord(char)
			return (0, None)
		elif iid == 0xe2:
			# Get a number of chars (as specified in RAX) and put them into stack
			nchars = int.from_bytes(self.computer.operatingsystem.processes[pid].threads[tid].registers['RAX'].data[0 : 4], byteorder='little')
			chars = getchars(nchars)
			# Place the chars
			self.computer.operatingsystem.processes[pid].threads[tid].stack.push(bytes(chars, ENCODING))
			# Recalculate RES
			self.computer.operatingsystem.processes[pid].threads[tid].registers['RES'].data[4 : 8] = int.to_bytes(len(self.computer.operatingsystem.processes[pid].threads[tid].stack.data), 4, byteorder='little')
			return (0, None)
	
	def update_screen(self):

		"""Update the data buffer to the screen."""

		# Clear and print the output
		clear()

		# Get a variable for the data
		data = self.computer.memory.memorypartitions[('perp', self.pid)].data

		newdata = ''

		# Iterate over each row
		for row in range(self.rows):
			# Get starting offset
			start = row * self.cols
			# Get ending offset
			end = start + self.cols
			# Add the data
			newdata += str(data[start : end], ENCODING)
			# Add a newline
			newdata += '\n'

		write(newdata)

		return (0, None)