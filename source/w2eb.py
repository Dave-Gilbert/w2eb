#!/usr/bin/python

import unicodedata
import time
import sys
import os
import json

from shutil import copyfile
from bs4 import BeautifulSoup
from bs4 import Comment

from w2ebUtils import *

from w2ebFootNotes import FootNotes
from w2ebFootNotes import Foot2HrefOk
from w2ebGenText import GenTextFootnote
from w2ebPic import PicGetImages
from w2ebStartup import Startup
from w2ebStartup import StartupReduceTags
from w2ebFinal import FinalMergeFootSectTOC


def MainSaveFile(opts, ipath, olist):
    """
    @summary: Save our new html file
    """

    ofile = open(ipath, "w+")
    
    ln = 0
    for oline in olist:
        ln += 1
        if opts['debug'] >= 3:
            ofile.write(oline)
        else:
            try:
                ofile.write(oline)
            except UnicodeEncodeError:
                # the following part is a bit harsh, but we need to do something
                # to recover. Hopefully we don't break the output. 
                ok_line = unicodedata.normalize('NFKD',oline).encode('ascii','ignore') 
                ofile.write(ok_line)            
            
    ofile.close()


def MainSketchHeading(heading):
    """
    @summary: Generate a normalized Version of a Heading 
    
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

def MainSketchParagraph(paragraph):
    """
    @summary: Generate a normalized Version of a Paragraph
    
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

    
def MainSketchPage(bl):
    """
    @summary: Combines heading and paragraph sketches in a single union
    
    @return: (sketch - a rough summary of a pages content)
    """
    
    sketch = set()
    
    for tag in bl.find_all('h1') + bl.find_all('h2') + bl.find_all('h3'):
        sktxt = MainSketchHeading(uGetTextSafe(tag))
        if sktxt:
            sketch = sketch.union({sktxt})

    for tag in bl.find_all('p'):
        sktxt = MainSketchParagraph(uGetTextSafe(tag))
        if sktxt:
            sketch = sketch.union({sktxt})

    return sketch

def MainParentSketchVsMySketch(parent_sketch, my_sketch):
    """
    @summary: Compare two page sketches.
    
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
    

def MainWelcomeMsg(opts, st_time):
    """
    @summary:  Print the welcom message for generating footnotes and sections
    """

    if not opts['footnote']:
        uPlog(opts, '')
        uPlog(opts, '---------------------------------------------')
    if opts['footnote']:
        uPlog(opts, '==> Fetching Summary for "' + opts['footsect_name'] + '"')
    else:
        uPlog(opts, '==> Downloading Wikibook "' + opts['footsect_name'] + '"')
        uPlog(opts, "Started at", time.asctime(time.localtime(st_time)))
    uPlog(opts, "Searching:", opts['url'])
    if opts['parent'] and not opts['footnote']:
        uPlog(opts,'Parent = "' + opts['parent'] + '"')

    if not opts['footnote']:
        ostr = "Debug = " + str(opts['debug']) + ", Depth = " + str(opts['depth'])
        if opts['no_images']:
            ostr += ", No Images =", str(opts['no_images'])
        if opts['svg2png']:
            ostr += ", .PNG Math & Figures"
        elif opts['svgfigs']:
            ostr += ", .SVG Math & .PNG Figures"
        else:
            None
        uPlog(opts, ostr)
        



def MainSummarize(opts, bl):
    """
    @summary: Summarize the article represented by bl. Save a representation in the footnote dir.
    
    @return (err, or a dictionary of footnote items)
    """
    
    err, foot_dict = GenTextFootnote(bl, opts)
    if foot_dict:
        fp = open(opts['base_bodir'] + '/footnotes/' + opts['ret_anch'] + '.json', 'w')
        if fp:
            json.dump(foot_dict, fp)
            fp.close()
        else:
            uPlog(opts, "Warning: unable to save footnote in cache, proceeding anyway")
# Not being able to cache a file should maybe create just a warning.

    return err, foot_dict
    # file that might be lingering




def MainSectionCreate(opts, st_time, bl, section_bname):

    st_time = time.time()
    im_tot = 0
    convert = 0
    slink = 0
    http404 = 0
    foot_dict_list = []
    foot_dict = {}

    StartupReduceTags(opts, bl, section_bname)
    im_tot, convert = PicGetImages(opts, bl) # easy...
    [sect_label_href_list, foot_dict_list, slink, http404] = FootNotes(opts, bl)

    sect_label_href_list = FinalMergeFootSectTOC(opts, st_time, bl, section_bname,
            im_tot, convert, slink, http404, foot_dict_list, sect_label_href_list)

    MainSaveFile(opts, opts['bodir'] + '/' + section_bname,
              bl.prettify(formatter="html").splitlines(True))
    
    return foot_dict_list, sect_label_href_list

def Main(opts):
    
    st_time = time.time()
    foot_dict_list = []
    foot_dict = {}
    sect_label_href_list = []
    
    opts['footsect_name'] = uCleanChars(opts, opts['footsect_name'])
    opts['bodir'] = uCleanChars(opts, opts['bodir'])
        
    
    if not opts['footnote']:
        uClean(opts)
    else:
        uSysMkdir(opts, opts['dcdir'])

    if opts['parent'] == '':
        opts['base_url'] = opts['url']
        opts['base_bodir'] = opts['bodir']

    err, bl, section_bname = uGetHtml(opts)
    
    if err:
        return err, [], []

    # Compare this section sketch to parents. Fail if they are too similar.    
    if not opts['footnote']:
        opts['my_sketch'] = MainSketchPage(bl)
        i_am_my_parent = MainParentSketchVsMySketch(opts['parent_sketch'], 
                                                    opts['my_sketch'])

        if i_am_my_parent:
            return 'similar_to_parent: ' + i_am_my_parent, None, None

    MainWelcomeMsg(opts, st_time)
    
    opts['section_bname'] = section_bname
    
    if opts['footnote']:
        err, foot_dict = MainSummarize(opts, bl)
        if not err:
            assert(foot_dict), \
                "Main: no foot_dict for footnote, but no error"
        foot_dict_list = [foot_dict]

    else:
        # When a section is complete therew will be a new directory on the disk
        foot_dict_list, sect_label_href_list = MainSectionCreate(opts, st_time, bl, section_bname)

    return err, foot_dict_list, sect_label_href_list
#
# Call our Main function
#

if __name__ == '__main__':

    opts = Startup()
    err, foot_dict_list, sect_label_href_list = Main(opts)
    if err:
        sys.exit(1)

