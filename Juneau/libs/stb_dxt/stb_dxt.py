#!/usr/bin/env python2

import os 
import ctypes
from PIL import Image
import numpy as np
import platform

# Get the path to the shared library
_dxt_path = ''
if platform.system().lower() == 'linux':
	_dxt_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'libs','linux','lib_stb_dxt.so')
elif platform.system().lower() == 'windows':
	_dxt_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),'libs','windows','stb_dxt.dll')
else:
	print("System is not supported")
	exit()
# Load the C-bindings
_dxt = ctypes.CDLL(_dxt_path)

def _get_compress_pixels_dst_size_bytes(w, h, is_rgba):

	_dxt.get_compress_pixels_dst_size_bytes.argtypes = (ctypes.c_uint64, ctypes.c_uint64, ctypes.c_bool)
	result = _dxt.get_compress_pixels_dst_size_bytes(ctypes.c_uint64(w), ctypes.c_uint64(h), ctypes.c_bool(is_rgba))
	return int(result)

# arrays provided and returned will be numpy arrays
def _compress_pixels(src, w, h, is_rgba):
	global _dxt

	dst_size = _get_compress_pixels_dst_size_bytes(w, h, is_rgba)
	dst = np.zeros(dst_size).astype(np.uint8)
	
	_dxt.compress_pixels.argtypes = (\
		ctypes.POINTER(ctypes.c_uint8), \
		ctypes.POINTER(ctypes.c_uint8), \
		ctypes.c_uint64, \
		ctypes.c_uint64, \
		ctypes.c_bool)

	result = _dxt.compress_pixels(\
		dst.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), \
		src.ctypes.data_as(ctypes.POINTER(ctypes.c_uint8)), \
		ctypes.c_uint64(w), \
		ctypes.c_uint64(h), \
		ctypes.c_bool(is_rgba))
	
	if not result: 
		return None

	return dst

# Get the raw compressed data for a given image.
# Returns None if unable to compress.
def get_compressed_image_bytes(image):

	# We are only able to compress RGB and RGBA
	is_rgba = False
	if (image.mode == "RGB"):
		is_rgba = False
		image = image.convert("RGBA")
	elif (image.mode == "RGBA"):
		is_rgba = True
	else:
		print("Can only compress RGB and RGBA images.");
		return None

	# Check to make sure the dimensions are multiples of 4
	# If not, resize
	if (image.width < 4 or image.width % 4 != 0 or \
		image.height < 4 or image.height % 4 != 0):
		print("Compressed images must have dimensions that are multiples of 4.")
		return None
		# w = int(np.ceil(np.max(image.width/4.0, 1)))*4
		# h = int(np.ceil(np.max(image.height/4.0, 1)))*4
		# image = image.Resize((w, h))
		# print("Resizing image to",w,"x",h)

	# Get the raw pixels
	# TODO: Which way do we flip?
	data = np.flip(np.array(image), axis=0)
	# Flatten the data
	data = data.flatten()
	# Compress the data
	compressed = _compress_pixels(data, image.width, image.height, is_rgba)
	if type(compressed) == type(None):
		print("Could not compress image")
		return None

	return compressed.tobytes()

# Compress a PIL Image
# Notes:
# - RGB images will be converted to DXT1
# - RGBA images will be converted to DXT5
def compress_image_to_file(image, save_path):

	# Get the image data
	data_bytes = get_compressed_image_bytes(image)
	if type(data_bytes) == type(None):
		return False

	# Save this data to a file
	with open(save_path,'wb') as file:
		file.write(data_bytes)
	return True