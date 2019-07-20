"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

from w2ebUtils import *

#
# All output is stored under the following directory
#

BASE_DIR = '/home/gilbert/Projects_Recent/wiki_books'

#
# Some temp files are created as part of image conversion. Store them here:
#

TMP_DIR = '/tmp/'

WGET_OPTS = """ \
 --timeout=10 \
 --tries=2 \
 --html-extension \
 --restrict-file-names=unix \
 --page-requisites \
 -k \
 --no-parent \
 --backups=0 \
 --level=0 \
 """

# wget has a habit of creating backups which is confusing for us when we are looking
# for exactly one .html file. Seems that we can't have '-k' without backups, so ..
# set the limit to 0

#
# Would like to use -nc, but it conflicts with -k, not sure why we need the conversion
#

# Page requisites doesn't work. We don't know why.
#
# We only get a single page and must manually download
# links etc. 
#

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

# A footnote link must have at least this many words to be included.
# we start looking for a natural end from here, i.e. a period or paragraph

MIN_WORDS = 15

# Maximum footnote length is 4 * min_words



# We collect as many as MAX_PAR pargraphs for the detailed note section

NOTE_MAX_PAR = 10

#
# When searching for a Table of contents we prefer old TOC locations, or 
# headings that say TOC. If we don't see anything like this after several
# paragraphs we simply insert our TOC at the beginning.#

TOC_MAX_PAR = 10

# footnotes must have no more than 10 paragraphs

MAX_PARAGRAPH = 10

IMAGE_PIC = ['.jpg', '.JPG', 'jpeg', 'JPEG']
IMAGE_FIG = ['.gif', '.GIF', '.png', '.PNG']
IMAGE_SVG = ['.svg', '.SVG']
SUFFIX_OT = ['.ico', '.php', '.pdf', '.PDF']

#
# There are a few bad images that we see regularly... 
#
IMAGE_AVOID = ['Special:CentralAutoLogin']

#
# There are a few bad links that always fail, just filter them 
#
LINK_AVOID = ['Special:BookSources']


W2EBID = 'w2eb_base_id'
W2EBRI = 'w2eb_ret_'
#
# I'm still struggling with this on. Basic example:
# x=u'\x139'
# print x   <--- gives us a funny symbol
#
# https://www.tutorialspoint.com/python/string_encode.htm

# https://docs.python.org/2/library/codecs.html#codec-base-classes
# and
# https://docs.python.org/2/library/codecs.html#standard-encodings


# Punctuation symbols are used to end summaries and headings in reasonable ways
# rather than just cutting them off. Once a word threshold is reached several 
# functions start looking for one of these symbols to wrap up a summary. 

Punc1 = ['.','?','!']           # good way to end a sentence
Punc2 = [',', ':', ';']        # less good
Punc3 = [')',']','}','>']       # ...
Punc4 = ['@','#','$','/','\\', '%','^','&','*','(','[','{','<']


