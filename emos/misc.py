"""

- EMOS 'misc.py' Source Code -

(C) Cubeflix 2021 (EMOS)

"""


# Imports
import time
import threading
import copy
import pickle
import shlex
import os, sys
import emos.parse
import hashlib
import json
import struct
import numpy as np
import multiprocessing


# Constants
MAXPROCESSMEMORY = 2 ** 32 - 1
MAXMEMORY = 2 ** 32 - 1
ENCODING = 'utf-8'
INVALID_FILENAME_CHARS = ['\n', '\b', '\t', '\r', '"', '\'']
FILEPATH = os.path.dirname(__file__)


class Exit(Exception):

	"""Exit exception. This is to be raised when an error occurs."""

	pass


class Interrupt(Exception):

	"""Interrupt exception. This is to be raised when a system interrupt is called."""

	pass


class SysError(Exception):

	"""The system error."""

	pass


def getsize(datadescriptor):

	"""Get the size of a data descriptor tuple."""

	if datadescriptor[0] == 'reg':
		size = datadescriptor[1][2]
	elif datadescriptor[0] == 'mem':
		size = datadescriptor[1][1]
	elif datadescriptor[0] == 'heap':
		size = datadescriptor[1][2]
	elif datadescriptor[0] == 'perp':
		size = datadescriptor[1][2]
	elif datadescriptor[0] == 'pmem':
		size = datadescriptor[1][2]
	else:
		return (15, "Not a supported destination type.")	

	return (0, size)


def clear():

	"""Clear the screen."""

	os.system('cls' if os.name == 'nt' else 'clear')


def write(string):

	"""Write the string to standard out.
	   Args: string -> the string to write"""

	sys.stdout.write(string)
	sys.stdout.flush()


# Get the get char method

def getcharswin(n):

	"""Get N chars from standard input. (WINDOWS ONLY)"""

	string = ""
	i = 0
	# Loop until we get N chars
	while True:
		c = msvcrt.getch()
		if c == b'\x03':
			raise KeyboardInterrupt()
		try:
			string += str(c, ENCODING)
		except UnicodeDecodeError:
			continue
		i += 1
		if i == n:
			break
	return string


def getcharsposix(n):

	"""Get N chars from standard input. (POSIX Systems ONLY)"""
	
	fd = sys.stdin.fileno()
	oldSettings = termios.tcgetattr(fd)
	string = ""
	i = 0
	# Loop until we get N chars
	while i <= n:
		# Do some magic
		try:
			tty.setcbreak(fd)
			answer = sys.stdin.read(1)
			if answer == b'\x03':
				raise KeyboardInterrupt()
			try:
				string += str(answer, ENCODING)
			except UnicodeDecodeError:
				continue
		finally:
			termios.tcsetattr(fd, termios.TCSADRAIN, oldSettings)
			i += 1
	# Return string
	return string


# Get the correct system's getchar method
try:
	# Check Windows
	import msvcrt
	getchars = getcharswin
except:
	# Use POSIX
	import tty, termios
	getchars = getcharsposix
