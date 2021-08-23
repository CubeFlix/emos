"""

- EMOS 'screen.py' Source Code -

(C) Cubeflix 2021 (EMOS)

"""


# Imports
from .misc import *
from .memory import *
from .computer import *


class ScreenPeripheral(Peripheral):

	"""The main screen peripheral object."""

	def __init__(self, computer, width, height):

		"""Create the screen peripheral object.
		   Args: computer -> the computer the screen is attached to
		         width -> the width of the screen
		         height -> the height of the screen"""

		self.computer = computer
		self.width, self.height = width, height

	def start(self, pid):

		"""Initialize the screen.
		   Args: width -> the width of the screen
		         height -> the height of the screen"""

		self.pid = pid

		# Attempt to hide the Pygame welcome prompt
		try:
			os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
		except Exception as e:
			pass

		# Create the screen peripheral's designed memory
		self.computer.memory.add_memory_partition(('perp', self.pid), MemorySection('screen_data_' + str(self.pid), 3 * self.width * self.height + (1 + 1 + 2 + 2), bytes(3 * self.width * self.height + (1 + 1 + 2 + 2)))) 
		# Mouse first button state, Mouse second button state, mouse position X, Mouse position Y

		# Begin the program
		self.running = True
		p = multiprocessing.Process(target=self._run)
		p.daemon = True
		p.start()

	def _run(self):

		"""Internally run the screen's main loop."""

		try:
			# Import and initialize Pygame
			self.pygame = __import__("pygame")
			self.pygame.init()

			# Create the screen
			self.screen = self.pygame.display.set_mode((self.width, self.height))

			self.pygame.display.set_caption("[EMOS] SCREEN_PERIPHERAL_" + str(self.pid))

			icon_image = self.pygame.image.load(os.path.join(FILEPATH, 'images/icon.png'))
			self.pygame.display.set_icon(icon_image)
			
			# Main loop
			while self.running:
				# Event loop
				for event in self.pygame.event.get():
					# Read mouse input
					if event.type == self.pygame.MOUSEBUTTONDOWN:
						# Mouse button down
						if event.button == 1: # Left click
							self.computer.memory.memorypartitions[('perp', self.pid)].data[-6] = 1
						elif event.button == 3: # Right click
							self.computer.memory.memorypartitions[('perp', self.pid)].data[-5] = 1
					elif event.type == self.pygame.MOUSEBUTTONUP:
						# Mouse button up
						if event.button == 1: # Left click
							self.computer.memory.memorypartitions[('perp', self.pid)].data[-6] = 0
						elif event.button == 3: # Right click
							self.computer.memory.memorypartitions[('perp', self.pid)].data[-5] = 0

				# Get mouse position data
				mouse_x, mouse_y = self.pygame.mouse.get_pos()
				self.computer.memory.memorypartitions[('perp', self.pid)].data[-4 : -2] = int.to_bytes(mouse_x, 2, byteorder='little')
				self.computer.memory.memorypartitions[('perp', self.pid)].data[-2 : ] = int.to_bytes(mouse_y, 2, byteorder='little')

				self.screen.fill((0, 0, 0))

				# Read the memory
				data = self.computer.memory.memorypartitions[('perp', self.pid)].data[ : -6]
				# Create the Numpy array for the screen data
				data = np.reshape(list(data), (self.width, self.height, 3))
				# Create the surface
				surface = self.pygame.surfarray.make_surface(data)
				# Render the surface
				self.screen.blit(surface, (0, 0))
				
				self.pygame.display.flip()
		except Exception as e:
			# Exception
			self.computer.operatingsystem.log += '\n' + str(e)

	def end(self):

		"""Run ending protocols."""

		self.running = False

		self.pygame.quit()

		del self.pid

	def handle(self, iid, pid, tid):

		"""Handle an interrupt.
		   Args: iid -> the interrupt id
		         pid -> the pid of the process
		         tid -> the tid of the process"""

		# Get the width
		# Get the height

	def __repr__(self):

		"""Get the string representation of the peripheral."""

		return "<ScreenPeripheral>"

	def __str__(self):

		"""Get the string representation of the peripheral."""

		return self.__repr__()
