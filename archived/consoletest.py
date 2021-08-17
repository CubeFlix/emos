import sys
import os

def write(string):
	sys.stdout.write(string)
	sys.stdout.flush()

size = os.get_terminal_size()
rows, cols = size.lines, size.columns

data_to_add = b'Hello, world!'
data = bytes((rows * cols) * b' ')

data = data_to_add + data[len(data_to_add) : ]

for row in range(rows):
	start = row * cols
	end = start + cols
	write(str(data[start : end], 'utf-8'))
	write('\n')

