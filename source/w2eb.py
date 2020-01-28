#!/usr/bin/python

"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

import sys
import signal

from w2ebStartup import Startup
from w2ebMain import Main

#
# All output is stored under the following directory
#

BASE_DIR = '/home/gilbert/Projects_Recent/wiki_books'  # XXX for debugging, my personal output dir
# BASE_DIR = '.'

def SignalHandlerCtrlC(sig, frame):
    """
    A signal handler for Ctrl+C. Exit and print a message.
    
    @param sig: ignored
    @param frame: ignored
    
    @note: Without this often a subshell catches the Ctrl C and the script
    won't terminate
    """
    print '\n\nCaught Ctrl+C...\nexiting.'
    sys.exit(1)

if __name__ == '__main__':

    signal.signal(signal.SIGINT, SignalHandlerCtrlC)
    
    opts = Startup(BASE_DIR)
    err, foot_dict_list, sect_label_href_list = Main(opts)
    if err:
        sys.exit(1)

