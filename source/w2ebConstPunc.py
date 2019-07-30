"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""


# Punctuation symbols are used to end summaries and headings in reasonable ways
# rather than just cutting them off. Once a word threshold is reached several 
# functions start looking for one of these symbols to wrap up a summary. 

Punc1 = ['.','?','!']           # good way to end a sentence
Punc2 = [',', ':', ';']        # less good
Punc_lb = [')',']','}','>']       #
Punc3 = Punc_lb
Punc_rb = ['(','[','{','<']
Punc4 = ['@','#','$','/','\\', '%','^','&','*'] + Punc_rb
