# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import logging
import time

import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI


# Constants
SSD1351_I2C_ADDRESS = 0x3C	# 011110+SA0+RW - 0x3C or 0x3D
SSD1351_SETCONTRAST = 0x81
SSD1351_DISPLAYALLON_RESUME = 0xA4
SSD1351_DISPLAYALLON = 0xA5
SSD1351_NORMALDISPLAY = 0xA6
SSD1351_INVERTDISPLAY = 0xA7
SSD1351_DISPLAYOFF = 0xAE
SSD1351_DISPLAYON = 0xAF
SSD1351_SETDISPLAYOFFSET = 0xD3
SSD1351_SETCOMPINS = 0xDA
SSD1351_SETVCOMDETECT = 0xDB
SSD1351_SETDISPLAYCLOCKDIV = 0xD5
SSD1351_SETPRECHARGE = 0xD9
SSD1351_SETMULTIPLEX = 0xA8
SSD1351_SETLOWCOLUMN = 0x00
SSD1351_SETHIGHCOLUMN = 0x10
SSD1351_SETSTARTLINE = 0x40
SSD1351_MEMORYMODE = 0x20
SSD1351_COLUMNADDR = 0x21
SSD1351_PAGEADDR = 0x22
SSD1351_COMSCANINC = 0xC0
SSD1351_COMSCANDEC = 0xC8
SSD1351_SEGREMAP = 0xA0
SSD1351_CHARGEPUMP = 0x8D
SSD1351_EXTERNALVCC = 0x1
SSD1351_SWITCHCAPVCC = 0x2

# Scrolling constants
SSD1351_ACTIVATE_SCROLL = 0x2F
SSD1351_DEACTIVATE_SCROLL = 0x2E
SSD1351_SET_VERTICAL_SCROLL_AREA = 0xA3
SSD1351_RIGHT_HORIZONTAL_SCROLL = 0x26
SSD1351_LEFT_HORIZONTAL_SCROLL = 0x27
SSD1351_VERTICAL_AND_RIGHT_HORIZONTAL_SCROLL = 0x29
SSD1351_VERTICAL_AND_LEFT_HORIZONTAL_SCROLL = 0x2A


#?  SSD1351_DELAYS_HWFILL	    (3)
#? SSD1351_DELAYS_HWLINE       (1)

# SSD1351 Commands
SSD1351_SETCOLUMN = 0x15
SSD1351_SETROW = 0x75
SSD1351_WRITERAM = 0x5C
SSD1351_READRAM = 0x5D
SSD1351_SETREMAP = 0xA0
SSD1351_STARTLINE =	0xA1
SSD1351_DISPLAYOFFSET =	0xA2
SSD1351_DISPLAYALLOFF =	0xA4
SSD1351_DISPLAYALLON = 0xA5
SSD1351_NORMALDISPLAY = 0xA6
SSD1351_INVERTDISPLAY = 0xA7
SSD1351_FUNCTIONSELECT = 0xAB
SSD1351_DISPLAYOFF = 0xAE
SSD1351_DISPLAYON =	0xAF
SSD1351_PRECHARGE =	0xB1
SSD1351_DISPLAYENHANCE = 0xB2
SSD1351_CLOCKDIV = 0xB3
SSD1351_SETVSL = 0xB4
SSD1351_SETGPIO = 0xB5
SSD1351_PRECHARGE2 = 0xB6
SSD1351_SETGRAY = 0xB8
SSD1351_USELUT = 0xB9
SSD1351_PRECHARGELEVEL = 0xBB
SSD1351_VCOMH = 0xBE
SSD1351_CONTRASTABC = 0xC1
SSD1351_CONTRASTMASTER = 0xC7
SSD1351_MUXRATIO = 0xCA
SSD1351_COMMANDLOCK = 0xFD
SSD1351_HORIZSCROLL = 0x96
SSD1351_STOPSCROLL  = 0x9E
SSD1351_STARTSCROLL = 0x9F




class SSD1351Base(object):
	"""Base class for SSD1351-based OLED displays.  Implementors should subclass
	and provide an implementation for the _initialize function.
	"""

	def __init__(self, width, height, rst, dc=None, sclk=None, din=None, cs=None,
				 gpio=None, spi=None, i2c_bus=None, i2c_address=SSD1351_I2C_ADDRESS,
				 i2c=None):
		self._log = logging.getLogger('Adafruit_SSD1351.SSD1351Base')
		self._spi = None
		self._i2c = None
		self.width = width
		self.height = height
		self._pages = height/8
		self._buffer = [0]*(width*height)
		# Default to platform GPIO if not provided.
		self._gpio = gpio
		if self._gpio is None:
			self._gpio = GPIO.get_platform_gpio()
		# Setup reset pin.
		self._rst = rst
		self._gpio.setup(self._rst, GPIO.OUT)
		# Handle hardware SPI
		if spi is not None:
			self._log.debug('Using hardware SPI')
			self._spi = spi
			self._spi.set_clock_hz(8000000)
		# Handle software SPI
		elif sclk is not None and din is not None and cs is not None:
			self._log.debug('Using software SPI')
			self._spi = SPI.BitBang(self._gpio, sclk, din, None, cs)
		# Handle hardware I2C
		elif i2c is not None:
			self._log.debug('Using hardware I2C with custom I2C provider.')
			self._i2c = i2c.get_i2c_device(i2c_address)
		else:
			self._log.debug('Using hardware I2C with platform I2C provider.')
			import Adafruit_GPIO.I2C as I2C
			if i2c_bus is None:
				self._i2c = I2C.get_i2c_device(i2c_address)
			else:
				self._i2c = I2C.get_i2c_device(i2c_address, busnum=i2c_bus)
		# Initialize DC pin if using SPI.
		if self._spi is not None:
			if dc is None:
				raise ValueError('DC pin must be provided when using SPI.')
			self._dc = dc
			self._gpio.setup(self._dc, GPIO.OUT)

	def _initialize(self):
		raise NotImplementedError

	def command(self, c):
		"""Send command byte to display."""
		if self._spi is not None:
			# SPI write.
			self._gpio.set_low(self._dc)
			self._spi.write([c])
		else:
			# I2C write.
			control = 0x00   # Co = 0, DC = 0
			self._i2c.write8(control, c)

	def data(self, c):
		"""Send byte of data to display."""
		if self._spi is not None:
			# SPI write.
			self._gpio.set_high(self._dc)
			self._spi.write([c])
		else:
			# I2C write.
			control = 0x40   # Co = 0, DC = 0
			self._i2c.write8(control, c)

	def begin(self, vccstate=SSD1351_SWITCHCAPVCC):
		"""Initialize display."""
		# Save vcc state.
		self._vccstate = vccstate
		# Reset and initialize display.
		self.reset()
		self._initialize()
		# Turn on the display.
		self.command(SSD1351_DISPLAYON)

	def reset(self):
		"""Reset the display."""
		# Set reset high for a millisecond.
		self._gpio.set_high(self._rst)
		time.sleep(0.001)
		# Set reset low for 10 milliseconds.
		self._gpio.set_low(self._rst)
		time.sleep(0.010)
		# Set reset high again.
		self._gpio.set_high(self._rst)

	def display(self):
		"""Write display buffer to physical display."""
		self.command(SSD1351_SETCOLUMN)
		self.data(0)              # Column start address. (0 = reset)
		self.data(self.width-1)   # Column end address.
		self.command(SSD1351_SETROW)
		self.data(0)              # Page start address. (0 = reset)
		self.data(self.height-1)  # Page end address.
		# Write buffer data.
		if self._spi is not None:
			# Set DC high for data.
			self._gpio.set_high(self._dc)
			# Write buffer.
			self.command(SSD1351_WRITERAM)
			self._spi.write(self._buffer)

		else:
			for i in range(0, len(self._buffer), 16):
				control = 0x40   # Co = 0, DC = 0
				self._i2c.writeList(control, self._buffer[i:i+16])

	def image(self, image):
		"""Set buffer to value of Python Imaging Library image.  The image should
		be in 1 bit mode and a size equal to the display size.
		"""
		# if image.mode != '1':
		#	raise ValueError('Image must be in mode 1.')
		imwidth, imheight = image.size
		if imwidth != self.width or imheight != self.height:
			raise ValueError('Image must be same dimensions as display ({0}x{1}).' \
				.format(self.width, self.height))
		# Grab all the pixels from the image, faster than getpixel.
		pix = image.load()
		# Iterate through the memory pages
		index = 0
		for page in range(self.height):
			# Iterate through all x axis columns.
			for x in range(self.width):
				# Set the bits for the column of pixels at the current position.
				bits = 0
				# Don't use range here as it's a bit slow
				for bit in [0, 1, 2, 3, 4, 5, 6, 7]:
					bits = bits << 1
					bits |= 0 if pix[(x, page*8+7-bit)] == 0 else 1
				# Update buffer byte and increment to next byte.
				self._buffer[index] = bits
				index += 1

	def clear(self):
		"""Clear contents of image buffer."""
		self._buffer = [0]*(self.width*self.height)

	def set_contrast(self, contrast):
		"""Sets the contrast of the display.  Contrast should be a value between
		0 and 255."""
		if contrast < 0 or contrast > 255:
			raise ValueError('Contrast must be a value from 0 to 255 (inclusive).')
		self.command(SSD1351_CONTRASTMASTER)
		self.command(contrast)

	def dim(self, dim):
		"""Adjusts contrast to dim the display if dim is True, otherwise sets the
		contrast to normal brightness if dim is False.
		"""
		# Assume dim display.
		contrast = 0
		# Adjust contrast based on VCC if not dimming.
		if not dim:
			if self._vccstate == SSD1351_EXTERNALVCC:
				contrast = 0x9F
			else:
				contrast = 0xCF

	def invert(self):
		self.command(SSD1351_NORMALDISPLAY)

	def rawfill(self, x, y, w, h, fillcolor):
		if (x >= self.width) or (y >= self.height):
			return

		if y+h > self.height:
			h = self.height-y-1

		if x+w > self.width:
			w = self.width-x-1

		self.command(SSD1351_SETCOLUMN)
		self.data(x)
		self.data(x+w-1)
 		self.command(SSD1351_SETROW)
		self.data(y)
		self.data(y+h-1)
		#fill!
		self.command(SSD1351_WRITERAM)
		for num in range (0, w*h):
			self.data(fillcolor >> 8)
			self.data(fillcolor)
	
	def color565(self, r, g, b):
  		c = r >> 3
		c <<= 6
		c |= g >> 2
		c <<= 5
		c |= b >> 3
		return c

	def roughimage(self, image):
		self.command(SSD1351_SETCOLUMN)
		self.data(0)
		self.data(self.width - 1)
 		self.command(SSD1351_SETROW)
		self.data(0)
		self.data(self.height-1)
		#fill
		width, height = image.size
		rgb_image = image.convert('RGB')
		pix = rgb_image.load()
		self.command(SSD1351_WRITERAM)
		for row in range (0, height -1):
			for column in range (0, width-1):
				r,g,b = pix[column, row]
				print (column, row)
				color = self.color565(r,g,b)
				self.data( color >> 8)
				self.data( color )

class SSD1351_128_96(SSD1351Base):
	def __init__(self, rst, dc=None, sclk=None, din=None, cs=None, gpio=None,
				 spi=None, i2c_bus=None, i2c_address=SSD1351_I2C_ADDRESS,
				 i2c=None):
		# Call base class constructor.
		super(SSD1351_128_96, self).__init__(128, 96, rst, dc, sclk, din, cs,
											 gpio, spi, i2c_bus, i2c_address, i2c)

	def _initialize(self):
		# 128x96 pixel specific initialization.
		# My version
		self.command(SSD1351_COMMANDLOCK)  # set command lock
		self.data(0x12)
		self.command(SSD1351_COMMANDLOCK)  # set command lock
		self.data(0xB1)
		self.command(SSD1351_DISPLAYOFF)   # 0xAE
		self.command(SSD1351_CLOCKDIV)     # 0xB3
		self.command(0xF1)  				   # 7:4 = Oscillator Frequency, 3:0 = CLK Div Ratio (A[3:0]+1 = 1..16)
		self.command(SSD1351_MUXRATIO)
		self.data(127)
		self.command(SSD1351_SETREMAP)
		self.data(0x74)
		self.command(SSD1351_SETCOLUMN)
		self.data(0x00)
		self.data(0x7F)
		self.command(SSD1351_SETROW)
		self.data(0x00)
		self.data(0x7F)
		self.command(SSD1351_STARTLINE)  # 0xA1
		self.data(96)
		self.command(SSD1351_DISPLAYOFFSET) 	# 0xA2
		self.data(0x0)
		self.command(SSD1351_SETGPIO)
		self.data(0x00)
		self.command(SSD1351_FUNCTIONSELECT)
		self.data(0x01)                         #internal (diode drop)
		self.command(SSD1351_PRECHARGE)  		# 0xB1
		self.command(0x32)
		self.command(SSD1351_VCOMH)  			# 0xBE
		self.command(0x05)
		self.command(SSD1351_NORMALDISPLAY)  	# 0xA6
		self.command(SSD1351_CONTRASTABC)
		self.data(0xC8)
		self.data(0x80)
		self.data(0xC8)
		self.command(SSD1351_CONTRASTMASTER)
		self.data(0x0F)
		self.command(SSD1351_SETVSL)
		self.data(0xA0)
		self.data(0xB5)
		self.data(0x55)
		self.command(SSD1351_PRECHARGE2)
		self.data(0x01)
