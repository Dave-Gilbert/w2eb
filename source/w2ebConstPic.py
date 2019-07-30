"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

# Image categories that receive similar treatment

IMAGE_PIC = ['.jpg', '.JPG', 'jpeg', 'JPEG']
IMAGE_FIG = ['.gif', '.GIF', '.png', '.PNG']
IMAGE_SVG = ['.svg', '.SVG']
SUFFIX_OT = ['.ico', '.php', '.pdf', '.PDF']

# kindle pixel dimesions

WMAX = 580
HMAX = 790

# set HMAX to be a little less than full height so we always have some room for text
HMAX = int(.85 * HMAX)

# Don't scale images to a size smaller than this unless
# the source image is actually this small
#
MIN_IMAGEpxW = WMAX

# Factor to scale math formulas by, expressed in 'ex' meaning:
# Relative to the x-height of the current font (rarely used)
# We like to see about 30 rows on a Kindle with 1/2 space between
# so maybe HMAX / 30?
# 
# A value of 10 give a rough height of 20 pixels, which is a bit small,
# and mathe equations tend to look bad on this level. Recommend 25 be used.
#
# Screen dot pitch is 92, Kindle dpi = 167, so whatever we see on the screen
# will be about 1/3rd smaller on the Kindle

IM_SCALEex = 25

#
# Otherwise we assume dimensions are in pixels, meant for a display
# so we should at least double them.  

IM_SCALEpx = 3
IM_SCALEperc = str(int(IM_SCALEpx * 100)) + '%'


# don't scale by more than MAX_SCALEpx times to get a MIN_IMAGEpx

MAX_SCALEpx = 4
