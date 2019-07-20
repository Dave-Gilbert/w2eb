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

from w2ebUtils import *
from w2ebGenText import GenTextWordsFromTags
from w2ebGenText import GenTextMakeFootDict

def LocalReuseArticleFnote(opts, bl, tag_href):
    """
    Recognize and merge Wikipedia footnotes with our own.
    
    @note: Assume any refernce that starts '#cit_ref' is to a wikipedia footnote.
    """

    foot_title = ''
    foot_dict = {}
    err = ''
    tag_parent = None

    anch = tag_href['href'].split('#')[1] 

    assert anch[0:9] == 'cite_note', "bad href " + tag_href['href']
        
    # assume that the footnote points at a list item
    tag_note = bl.find('li', id=anch)
    
    if not tag_note:
        err = 'Cant find wikipedia local reference #' + anch
    if not err:
        tag_cont = tag_note.find('span', class_='reference-text')
        tag_parent = tag_note.parent
        if not tag_cont:
            err = 'Cant find wikipedia reference-text #' + anch
    if not err:
        tag_cont.prettify(formatter="html")

    if not err:
    
        assert 1, "Use code from w2ebGenText for this section"

        if len(anch) > 10:
            ret_anch = uGenRetAnch(opts, anch[10:])
        else:
            ret_anch = uGenRetAnch(opts, str(opts['footi']))

        foot_title = tag_href.string.replace('[','').replace(']','')
        
        number = False
        try:
            if int(foot_title) == int(foot_title):
                number = True
        except Exception:
            None
        
        if number:
            # Most wikipedia footnotes are just numbers, but not all... 
            tag_href.string = '[' + str(opts['footi']) + ']'
            foot_title = ''
            
        words, note_list = GenTextWordsFromTags(tag_cont, True)
        
        notes = 'never'
        if note_list:
            foot_dict = GenTextMakeFootDict(note_list, ret_anch, '',
                                            foot_title, 'never')
            opts['footi'] += 1
            tag_href.string = foot_title
            tag_href['href'] = '#' + ret_anch + '_foot'
            tag_note.decompose()
        
            uPlogExtra(opts,"Reassigning local anchor %s to %s" % (anch, ret_anch), 2)
        else:
            tag_href.name = 'i'
            err = "Unable to Reassign local anchor %s" % anch
        
    return err, foot_dict, tag_parent

def LocalAndRecognized(opts, tag_href):
    """
    Recognize and merge Wikipedia local references with our own, if we can.
    
    @note: Assume any refernce that starts '#cit_ref' is to a wikipedia footnote.
    """
    
    if not tag_href.has_attr('href'):
        return False
    
    url = tag_href['href']

    if '#' in url:
        bname = url.split('#')[0]
        anch = url.split('#')[1] 
    else:
        return False
    
#    if 'cite' in anch:
#        print "YYYa", bname, opts['section_bname'], anch
    
    if bname.lower() in opts['section_bname'].lower() and anch[0:9] == 'cite_note':
        return True
    
    return False

def LocalReuse(opts, bl):

    foot_dict_list = []
    i = 0
    r = 0
    im_all = 0

    uPlog(opts,'')
    st_time = time.time()
    
    uPlog(opts, 'Reassigning existing footnotes (r)')
    sys.stdout.flush()
    uPlogExtra(opts, '', 1)
    parent = None

    for tag_href in bl.find_all(lambda x: LocalAndRecognized(opts, x)):
        im_all += 1
    
    p_total_est_time = im_all / 10.0
    
    # uPrintProgress(opts, st_time, 0, im_all, p_total_est_time)
    
    for tag_href in bl.find_all(lambda x: LocalAndRecognized(opts, x)):

        err, foot_dict, tag_parent = LocalReuseArticleFnote(opts, bl, tag_href)

        if not err:            
            foot_dict_list.append(foot_dict)
            psym = 'r'
            r += 1
            parent = tag_parent
        else:
            uPlogExtra(opts, err, 2)
            psym = '-'

        if i % 25 == 0:
            p_total_est_time = uPrintProgress(opts, st_time, i,
                                              im_all, p_total_est_time)

        uPlogNr(opts, psym)
        i = i + 1
        sys.stdout.flush()

    tag_parent.decompose()

    uPlog(opts, '\nReassigned %d footnotes' % r)
    sys.stdout.flush()
    uPlogExtra(opts, '', 1)

    return foot_dict_list











