"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

from w2ebUtils import uGetTextSafe

def SketchHeading(heading):
    """
    Generate a normalized Version of a Heading 
    
    @note: Convert a title like '1.0 Important Dates' to a normalized format
    which ignores all symbols, punctuation and upper and lower case
    """
    ol = heading.split(' ')
    
    rval =''
    for w in ol:
        if not w.isalpha():
            continue
        w = w.title().strip()
        rval += w
    
    return rval

def SketchParagraph(paragraph):
    """
    Generate a normalized Version of a Paragraph
    
    @note: Take the first 8 words in a paragraph and normalize them by
    ignoring all symbols, punctuation and upper and lower case.
    """
    ol = paragraph.split(' ')
    
    rval =''
    twords = 0
    i = 0
    while twords < 8 and i < len(ol):
        w = ol[i]
        i += 1
        if not w.isalpha():
            continue
        twords += 1
        rval += w
    
    return rval

    
def SketchPage(bl):
    """
    Combines heading and paragraph sketches in a single union
    
    @return: (sketch - a rough summary of a pages content)
    """
    
    sketch = set()
    
    for tag in bl.find_all('h1') + bl.find_all('h2') + bl.find_all('h3'):
        sktxt = SketchHeading(uGetTextSafe(tag))
        if sktxt:
            sketch = sketch.union({sktxt})

    for tag in bl.find_all('p'):
        sktxt = SketchParagraph(uGetTextSafe(tag))
        if sktxt:
            sketch = sketch.union({sktxt})

    return sketch

def SketchVsMySketch(parent_sketch, my_sketch):
    """
    Compare two page sketches.
    
    @return: None if they are different, a score if similarity is > 75%
    """

    sim = 0
    tot = 0
    
    if not parent_sketch:
        return False
    
    for item in my_sketch:
        tot += 1
        if item in parent_sketch:
            sim += 1
        
    if 1.0 * sim / tot > 0.75:
        return "s_score = %d / %d = %3.2f" % (sim, tot, 1.0 * sim / tot)
    
    return ""
    
