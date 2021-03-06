"""

- EMOS 'parse.py' Source Code -

(C) Cubeflix 2021 (EMOS)

"""

import string
import math
import os
import struct

ENCODING = 'utf-8'
REGISTER_NAMES = ['RAX', 'RCX', 'RDX', 'RBX', 'RSP', 'RBP', 'RSI', 'RDI', 'RIP', 'CS', 'DS', 'SS', 'ES', 'FLAGS', 'R8', 'R9', 'R10', 'R11', 'R12', 'R13', 'R14', 'R15']
CHARS_HEX = '0123456789abcdefABCDEF'
CHARS_DEC = '0123456789'
MNEMONIC_LIST = ['MOV', 'ADD', 'SUB', 'MUL', 'SMUL', 'DIV', 'SDIV', 'AND', 'OR', 'XOR', 'NOT', 'PUSH', 'POP', 'ADDF', 'SUBF', 'MULF', 'SMULF', 'DIVF', 'SDIVF', 'ANDF', 'ORF', 'XORF', 'NOTF', 'JMP', 'CMP', 'SCMP', 'JL', 'JG',
				 'JE', 'JLE', 'JGE', 'JNE', 'NOP', 'HLT', 'CALL', 'RET', 'SYS', 'POPN', 'PUSHN', 'INFL', 'INT', 'ARGN', 'LIB', 'BSL', 'ASL', 'BSLF', 'ASLF', 'BSR', 'ASR', 'BSRF', 'ASRF', 'EIR', 'ML', 'MG', 'ME', 'MLE', 'MGE', 
				 'MNE', 'POPR', 'POPNR', 'VARN', 'OFFSG', 'ADDFLOAT', 'SUBFLOAT', 'MULFLOAT', 'DIVFLOAT', 'POWFLOAT', 'CMPFLOAT', 'ITF', 'SITF', 'FTI', 'FTSI']
STD_LIBS = ['ISLIB', 'WRITELIB', 'FSLIB']


class ParseError(Exception):

	"""A base error for all parsing exceptions."""

	pass


class Compiler:

	"""Compiles code."""

	def __init__(self, code, filesys='comp', emos=None, currentdir=None):

		"""Create the Compiler.
		   Args: code -> code to parse and compile
		         filesys -> the file system to load other files from. 'comp' is for computer, and 'emos' is for EMOS. 
		         emos -> the operating system to retrieve files from
		         currentdir -> the current working directory for emos"""

		self.code = code
		self.filesys = filesys
		self.emos = emos
		self.currentdir = currentdir

		self.tree = [['SEC', 'code']]

	def next_char(self):

		"""Pop off the next character."""

		try:
			char = self.code[0]
			self.code = self.code[1 : ]
			return char
		except:
			raise ParseError('Ran out of input, excepted more.')

	def next_chars(self, num_chars):

		"""Pop off num_chars chars."""

		try:
			chars = self.code[ : num_chars]
			self.code = self.code[num_chars : ]
			return chars
		except:
			raise ParseError('Ran out of input, excepted more.')

	def scan_char(self):

		"""Get the next char."""

		try:
			return self.code[0]
		except:
			raise ParseError('Ran out of input, expected more.')

	def scan_chars(self, num_chars):

		"""Get the next chars."""

		try:
			return self.code[ : num_chars]
		except:
			raise ParseError('Ran out of input, expected more.')

	def parse_through_whitespace(self, allow_comments=False):

		"""Remove useless whitespace."""

		had_comment = False

		while True:
			# Remove whitespace
			self.code = self.code.lstrip()
			if self.code and self.scan_char() == '#':
				# Next is a comment
				if allow_comments:
					had_comment = True
					self.parse_until_char('\n')
				else:
					raise ParseError("Comment not expected.")
			else:
				# Stop parsing, or we'll get into real code
				break

		return had_comment

	def parse_through_whitespace_nonewline(self, allow_comments=False):

		"""Remove useless whitespace, but not newlines."""

		had_comment = False

		while True:
			# Remove whitespace
			self.code = self.code.lstrip(' ').lstrip('\t')
			if self.code and self.scan_char() == '#':
				# Next is a comment
				if allow_comments:
					had_comment = True
					self.parse_until_char('\n')
				else:
					raise ParseError("Comment not expected.")
			else:
				# Stop parsing, or we'll get into real code
				break

		return had_comment

	def parse_through_string(self, starting_char):

		"""Parse a string.
		   Args: starting_char -> the starting character that the string started with"""

		chars = ''

		# Iterate until stopping
		while True:
			# Get one char
			current_char = self.next_char()
			# Check if we should end
			if current_char == starting_char:
				break
			# Check for a forward slash
			if current_char == '\\':
				# We should check the next character
				next_char = self.next_char()
				# Check for a 'n'
				if next_char == 'n':
					# Add a newline
					chars += '\n'
					continue
				elif next_char == 'b':
					# Add a backspace
					chars += '\b'
					continue
				elif next_char == 't':
					# Add a tab
					chars += '\t'
					continue
				elif next_char == 'r':
					# Add a line return
					chars += '\r'
					continue
				# Else, add the next char and ignore it
				chars += next_char
				continue
			# Else, add the char normally
			chars += current_char

		# When we are done, return the string
		return chars

	def parse_until_char(self, char):

		"""Parse until we get to a specific character.
		   Args: char -> the char to wait for"""

		chars = ''

		# Iterate through until we get to char
		while True:
			if not self.code:
				break
			current_char = self.scan_char()
			# Check for the special char
			if current_char == char:
				break
			else:
				# Add the char
				self.next_char()
				chars += current_char

		# Return the string
		return chars

	def parse_until_non_alpha(self):

		"""Parse until we get to a non-alpha character (not in the alphabet)."""

		chars = ''

		# Iterate through until we get to non alpha
		while True:
			if not self.code:
				break
			current_char = self.scan_char()
			# Check for the special char
			if current_char not in string.ascii_letters:
				break
			else:
				# Add the char
				self.next_char()
				chars += current_char

		# Return the string
		return chars

	def parse_until_non_alphanumeric(self):

		"""Parse until we get to a non-alphanumeric character (not in the alphabet or numbers)."""

		chars = ''

		# Iterate through until we get to non alpha
		while True:
			if not self.code:
				break
			current_char = self.scan_char()
			# Check for the special char
			if current_char not in string.ascii_letters + '0123456789':
				break
			else:
				# Add the char
				self.next_char()
				chars += current_char

		# Return the string
		return chars

	def parse_until_non_hex(self):

		"""Parse until we get a non-hexadecimal character (not in the hex system of 0123456789abcdefABCDEF)"""

		chars = ''

		# Iterate through until we get to non hex
		while True:
			if not self.code:
				break
			current_char = self.scan_char()
			# Check for the special char
			if current_char not in CHARS_HEX:
				break
			else:
				# Add the char
				self.next_char()
				chars += current_char

		# Return the string
		return chars

	def parse_until_non_numeric(self):

		"""Parse until we get a non-numeric character (not in the decimal system of 0123456789)"""

		chars = ''

		# Iterate through until we get to non hex
		while True:
			if not self.code:
				break
			current_char = self.scan_char()
			# Check for the special char
			if current_char not in CHARS_DEC:
				break
			else:
				# Add the char
				self.next_char()
				chars += current_char

		# Return the string
		return chars

	def parse_until_non_defined(self, defined):

		"""Parse until we get a char not in the defined list."""

		chars = ''

		# Iterate through until we get to non hex
		while True:
			if not self.code:
				break
			current_char = self.scan_char()
			# Check for the special char
			if current_char not in defined:
				break
			else:
				# Add the char
				self.next_char()
				chars += current_char

		# Return the string
		return chars

	def parse_arg(self):

		"""Parse an argument."""

		arg = []

		# Get the data type
		type_data = self.parse_until_non_alpha().upper()
		self.parse_through_whitespace_nonewline()

		# Check if the type is 'REG' or register
		if type_data == 'REG':
			# Parse a register i.e. REG[RAX, [0x00] : [0x04]]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Parse through to get register name
			self.parse_through_whitespace_nonewline()
			reg_id = REGISTER_NAMES.index(self.parse_until_non_alphanumeric().upper())
			arg.append(reg_id)
			# Get ','
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ',':
				raise ParseError('Missing \',\'')
			# Parse through to get the starting position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ':'
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ':':
				raise ParseError('Missing \':\'')
			# Get ending position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['REG', arg]
		# Check if the type is '' or a intermediate type
		elif type_data == '':
			# Parse an intermediate value, i.e. [0x0013, 'ABC!', 4d12345]
			data = bytearray()
			# Get the opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Iterate over each element
			while True:
				self.parse_through_whitespace_nonewline()
				# Ensure that it isn't a '[]'
				if self.scan_char() == ']':
					self.next_char()
					break
				# Check for the '0x' bit for hexadecimal
				if self.scan_chars(2) == '0x':
					self.next_chars(2)
					# Get the rest of the number
					current_hex = self.parse_until_non_hex()
					current_bit = int.to_bytes(int(current_hex, 16), math.ceil(len(current_hex) / 2), byteorder='little')
					data += current_bit
				# Check for the 'Xd' bit for decimal
				elif self.scan_chars(2)[1] == 'd' and self.scan_char() in CHARS_DEC:
					# Get number of bytes
					nbytes = int(self.next_char())
					# Get the 'd'
					self.next_char()
					# Get the rest of the number
					current_dec = self.parse_until_non_numeric()
					current_bit = int.to_bytes(int(current_dec), nbytes, byteorder='little')
					data += current_bit
				# Check for a 'XX' bit for 4-byte decimal
				elif self.scan_chars(2).isnumeric() or (self.scan_chars(2)[0].isnumeric() and not self.scan_chars(2)[1] in ('x', 'd')):
					# Get the number
					num = int(self.parse_until_non_numeric())
					data += int.to_bytes(num, 4, byteorder='little')
				# Check for a 'f' bit for 4-byte float
				elif self.scan_char() == 'f':
					self.next_char()
					# Get the number
					current_dec = self.parse_until_non_defined('0123456789.')
					current_bit = struct.pack('f', float(current_dec))
					data += current_bit
				# Check for a opening quotation for a string
				elif self.scan_char() in ('\'', '"'):
					# Get the string
					current_string = self.parse_through_string(self.next_char())
					current_bit = bytes(current_string, ENCODING)
					data += current_bit
				# Else, raise an error
				else:
					raise ParseError('Not a supported data type for an intermediate type.')
				# Remove useless whitespace
				self.parse_through_whitespace_nonewline()
				# Check if it's a ']' or a ','
				nextchar = self.next_chars(1)
				if nextchar == ']':
					# End the parsing
					break
				elif nextchar == ',':
					# Continue parsing
					continue
				else:
					raise ParseError('Expected a \',\' or \']\'.')
			arg.append(data)
			return ['INT', arg]
		# Check if the type is a 'MEM' or a memory type
		elif type_data == 'MEM':
			# Parse a memory bit i.e. MEM[[0x00] : [0x04]]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Parse through to get the starting position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ':'
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ':':
				raise ParseError('Missing \':\'')
			# Get ending position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['MEM', arg]
		elif type_data == 'SYM':
			# Parse a symbol to resolve later i.e. SYM[begin_prog]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Parse through to get the starting position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_until_non_defined(string.ascii_letters + '_-0123456789'))
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['SYM', arg]
		# Check if the type is a 'HEAP' or a heap memory type
		elif type_data == 'HEAP':
			# Parse a memory bit i.e. HEAP[[0x0], [0x0] : [0x4]]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Get the heap ID
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ','
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ',':
				raise ParseError('Missing \',\'')
			# Parse through to get the starting position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ':'
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ':':
				raise ParseError('Missing \':\'')
			# Get ending position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['HEAP', arg]
		# Check if the type is a 'PERP' or a peripheral memory type
		elif type_data == 'PERP':
			# Parse a memory bit i.e. PERP[[0x0], [0x0] : [0x4]]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Get the peripheral ID
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ','
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ',':
				raise ParseError('Missing \',\'')
			# Parse through to get the starting position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ':'
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ':':
				raise ParseError('Missing \':\'')
			# Get ending position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['PERP', arg]
		# Check if the type is a 'R' or lower shorthand register type
		elif type_data == 'R':
			# Parse a shorthand register bit i.e. R[RAX] -> REG[RAX, [0x0] : [0x4]]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Get the register name
			self.parse_through_whitespace_nonewline()
			reg_id = REGISTER_NAMES.index(self.parse_until_non_alphanumeric().upper())
			arg.append(reg_id)
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['R', arg]
		# Check if the type is a 'U' or upper shorthand register type
		elif type_data == 'U':
			# Parse a shorthand register bit i.e. U[RAX] -> REG[RAX, [0x4] : [0x4]]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Get the register name
			self.parse_through_whitespace_nonewline()
			reg_id = REGISTER_NAMES.index(self.parse_until_non_alphanumeric().upper())
			arg.append(reg_id)
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['U', arg]
		# Check if the type is a 'PROC' or process memory type
		elif type_data == 'PROC':
			# Parse a process memory type i.e. PROC[[0], [0x0] : [0x4]]
			# Get opening bracket
			if self.next_char() != '[':
				raise ParseError('Missing \'[\'')
			# Get the process ID
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ','
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ',':
				raise ParseError('Missing \',\'')
			# Parse through to get the starting position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ':'
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ':':
				raise ParseError('Missing \':\'')
			# Get ending position
			self.parse_through_whitespace_nonewline()
			arg.append(self.parse_arg())
			# Get ending bracket
			self.parse_through_whitespace_nonewline()
			if self.next_char() != ']':
				raise ParseError('Missing \']\'')
			return ['PROC', arg]
		else:
			raise ParseError('Undefined type.')

	def parse(self):

		"""Parse the code."""

		# Iterate through the code
		while self.code:
			# Clear unnecessary spaces
			if self.parse_through_whitespace(allow_comments=True):
				continue
			if not self.code:
				break
			# Get the opcode/mnemonic
			mnemonic = self.parse_until_non_alpha()
			if mnemonic:
				# We have a command line
				# Clear unnecessary spaces but not newlines, so we don't cut to a different opcode
				if self.parse_through_whitespace_nonewline(allow_comments=True):
					break
				# Get each argument
				args = []
				while True:
					# Check if we get a newline
					if not self.code or self.scan_char() == '\n':
						break
					elif self.scan_char() == '#':
						self.parse_through_whitespace(allow_comments=True)
						break
					# Parse the arg
					args.append(self.parse_arg())
					# Remove unnecessary spaces
					if self.parse_through_whitespace_nonewline(allow_comments=True):
						break
					# Check if we get a comma
					if self.code and self.scan_char() == ',':
						self.next_char()
						self.parse_through_whitespace_nonewline()
						continue
					else:
						self.parse_through_whitespace_nonewline(allow_comments=True)
						break
				# Add this to the tree
				if mnemonic.upper() == 'DATA':
					# Data definition
					self.tree.append(['DATA', args])
				else:
					self.tree.append([MNEMONIC_LIST.index(mnemonic.upper()), args])
			elif self.scan_char() == '[':
				# We have a label line
				if self.next_char() != '[':
					raise ParseError('Missing \'[\'')
				# Parse through to get the label name
				self.parse_through_whitespace_nonewline()
				label_name = self.parse_until_non_defined(string.ascii_letters + '_-0123456789')
				if label_name == '':
					# Section declaration
					if self.next_char() != '.':
						raise ParseError('Expected \'.\' for section declaration')
					section_name = self.parse_until_non_defined(string.ascii_letters + '_-0123456789')
					# Get the closing bracket
					self.parse_through_whitespace_nonewline()
					if self.next_char() != ']':
						raise ParseError('Missing \']\'')
					self.parse_through_whitespace_nonewline(allow_comments=True)
					self.tree.append(['SEC', section_name])
				else:
					self.tree.append(['LABL', label_name])
					# Get the closing bracket
					self.parse_through_whitespace_nonewline()
					if self.next_char() != ']':
						raise ParseError('Missing \']\'')
					# Check for comments
					if self.parse_through_whitespace_nonewline(allow_comments=True):
						# Comment, so escape
						continue
					else:
						# We had no comment, so check next char
						if self.scan_char == '\n':
							# Newline, so escape
							continue
						else:
							# We have a variable
							args = []
							while True:
								# Check if we get a newline
								if not self.code or self.scan_char() == '\n':
									break
								# Parse the arg
								args.append(self.parse_arg())
								# Remove unnecessary spaces
								if self.parse_through_whitespace_nonewline(allow_comments=True):
									break
								# Check if we get a comma
								if self.code and self.scan_char() == ',':
									self.next_char()
									self.parse_through_whitespace_nonewline()
									continue
								else:
									self.parse_through_whitespace_nonewline(allow_comments=True)
									break
							self.tree.append(['DATA', args])
			elif self.scan_char() == '<':
				# We have a include directive
				if self.next_char() != '<':
					raise ParseError('Missing \'<\'')
				# Get the include name
				self.parse_through_whitespace_nonewline()
				if self.scan_char() == '"':
					# File include
					filename = self.parse_through_string(self.next_char())
					# Get the file data
					if self.filesys == 'comp':
						# Computer file system
						file = open(filename, 'r')
						filedata = file.read()
						file.close()
					elif self.filesys == 'emos':
						# EMOS file system
						if filename.startswith('/') or filename.startswith('\\'):
							# Absolute path
							exitcode, filedata = self.emos.computer.filesystem.read_file(filename)
							if exitcode != 0:
								raise ParseError("Invalid path.")
							filedata = str(filedata, ENCODING)
						else:
							# Relative path
							exitcode, filedata = self.emos.computer.filesystem.read_file(os.path.join(self.currentdir, filename))
							if exitcode != 0:
								raise ParseError("Invalid path.")
							filedata = str(filedata, ENCODING)
					# Eat the ending char
					self.parse_through_whitespace_nonewline()
					if self.next_char() != '>':
						raise ParseError("Missing '>'")
					# Add the code
					self.code = filedata + self.code
				else:
					# Library include
					libname = self.parse_until_non_alpha().upper()
					self.tree += [['SEC', 'code'], [11, [['R', [0]]]], [11, [['R', [3]]]], [0, [['R', [0]], ['INT', [bytearray(b'\r\x00\x00\x00')]]]], [0, [['R', [3]], ['INT', [int.to_bytes(STD_LIBS.index(libname), 4, byteorder='little')]]]], 
									[36, []], [51, []], [12, [['R', [3]]]], [12, [['R', [0]]]]]
					# Eat the ending char
					self.parse_through_whitespace_nonewline()
					if self.next_char() != '>':
						raise ParseError("Missing '>'")
			else:
				raise ParseError("Invalid line.")

		return self.tree

	def compile_arg(self, arg):

		"""Compiles an argument.
		   Args: atype -> the type of the argument"""

		atype = arg[0].upper()
		data = arg[1]

		# We have to add data bit by bit because we need to catch symbols. 

		# Register
		if atype == 'REG':
			# Type: 0, RegName: data[0], Start: data[1], End: data[2]
			self.compiled += bytearray([0])
			self.compiled += bytearray([data[0]])
			self.compile_arg(data[1])
			self.compile_arg(data[2])
		# Process memory
		elif atype == 'MEM':
			# Type: 1, Start: data[0], End: data[1]
			self.compiled += bytearray([1]) 
			self.compile_arg(data[0]) 
			self.compile_arg(data[1])
		# Intermediate
		elif atype == 'INT':
			# Type: 2, Data: data[0]
			self.compiled += bytearray([2]) 
			self.compiled += int.to_bytes(len(data[0]), 2, 'little')
			self.compiled += data[0]
		# Label/Symbol
		elif atype == 'SYM':
			# Type: 2, Data: zeros for now, but we will add then in later
			self.compiled += bytearray([2])
			self.compiled += bytearray([4, 0])
			# Add this label access to the label_uses
			self.label_uses[len(self.compiled)] = data[0]

			self.compiled += bytearray([0, 0, 0, 0])
		# Heap memory
		elif atype == 'HEAP':
			# Type: 3, HeapID: data[0], Start: data[1], End: data[2]
			self.compiled += bytearray([3])
			self.compile_arg(data[0]) 
			self.compile_arg(data[1])
			self.compile_arg(data[2])
		# Peripheral memory
		elif atype == 'PERP':
			# Type: 4, PerpID: data[0], Start: data[1], End: data[2]
			self.compiled += bytearray([4])
			self.compile_arg(data[0]) 
			self.compile_arg(data[1])
			self.compile_arg(data[2])
		# Lower register
		elif atype == 'R':
			# Type: 5, RegName: data[0]
			self.compiled += bytearray([5])
			self.compiled += bytearray([data[0]])
		# Upper register
		elif atype == 'U':
			# Type: 6, RegName: data[0]
			self.compiled += bytearray([6])
			self.compiled += bytearray([data[0]])
		# Other process memory
		elif atype == 'PROC':
			# Type: 7, PID: data[0], Start: data[1], End: data[2]
			self.compiled += bytearray([7])
			self.compile_arg(data[0]) 
			self.compile_arg(data[1])
			self.compile_arg(data[2])

	def compile_data(self, data):

		"""Compiles a data argument.
		   Args: data -> the data argument"""

		atype = data[0].upper()
		data = data[1]

		# Intermediate
		if atype == 'INT':
			self.compiled += data[0]
		else:
			raise ParseError("Data has to have intermediate type.")

	def rearrange_tree(self):

		"""Rearranges the syntax tree so that all code sections are at the top and the data sections are at the bottom."""

		code_sec = []
		data_sec = []

		mode = ''

		# Iterate over each command
		for command in self.tree:
			# Section
			if command[0] == 'SEC':
				mode = command[1]
				if mode == 'code':
					code_sec.append(command)
				elif mode == 'data':
					data_sec.append(command)
			# Anything else
			else:
				if mode == 'code':
					code_sec.append(command)
				elif mode == 'data':
					data_sec.append(command)
				else:
					raise ParseError("Only code and data sections are permitted.")

		self.tree = code_sec + data_sec

	def compile(self):

		"""Compiles the code in the tree."""

		self.compiled = bytearray()

		self.rearrange_tree()
		
		self.labels = {}
		self.label_uses = {}

		self.data_index = None

		mode = 'code'

		# Pass one (compiling)
		for line in self.tree:
			# Check for an opcode
			if type(line[0]) == int:
				# Add the opcode to the compiled code
				self.compiled += bytearray([line[0]])
				# Add the arguments
				for arg in line[1]:
					# Add the argument
					self.compile_arg(arg)
			# Check for a symbol/label definition
			elif line[0] == 'LABL':
				# Add the label to the labels
				self.labels[line[1]] = len(self.compiled)
			# Check for a DATA definition
			elif line[0] == 'DATA':
				# Parse the arg
				for arg in line[1]:
					# Add the argument
					self.compile_data(arg)
			# Check for a section definition
			elif line[0] == 'SEC':
				mode = line[1]
				if mode == 'data' and self.data_index == None:
					# Move to data section
					self.data_index = len(self.compiled)

		# Pass two (resolving labels/symbols)

		self.labels = {**self.labels, **{'DATA' : self.data_index, 'CODE' : 0}}

		for index, name in self.label_uses.items():
			# Find the resolved label/symbol
			resolved = self.labels[name]
			# Place the label there
			self.compiled[index : index + 4] = int.to_bytes(resolved, 4, byteorder='little')

		return self.compiled, self.data_index

