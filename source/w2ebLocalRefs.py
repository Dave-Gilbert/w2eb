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

from bs4 import NavigableString

from w2ebUtils import *
from w2ebGenText import GenTextWordsFromTags
from w2ebGenText import GenTextMakeFootDict

def LocalRaiseAnchor(tag_href, ret_anch):
    """
    Raise the anchor to a location shortly before the reference
    
    @note: Kindle often needs an id to appear a little before the text that
           it anchors. Put return id in previous sibling or parent if possible.

    """

    if (tag_href.previous_sibling and not isinstance(tag_href.previous_sibling, NavigableString) and 
        not tag_href.previous_sibling.has_attr('id')):
        tag_href.previous_sibling['id'] = ret_anch
    elif not tag_href.parent.has_attr('id'):
        tag_href.parent['id'] = ret_anch
    else:
        tag_href['id'] = ret_anch


def LocalReuseArticleFnoteCache(opts, tag_href, foot_dict_list):
    """
    Keep a list of already visited footnotes, check for the original ref
    
    @return: T/F whether the reference was found in the existing list.
    """

    found = False
    anch = tag_href['href'].split('#')[1] 

    assert anch[0:9] == 'cite_note', "bad href " + tag_href['href']
        
    for foot_dict in foot_dict_list:
        if anch == foot_dict['orig_anch']:
            found = True
            tag_href.string = foot_dict['foot_title']
            tag_href['href'] = '#' + foot_dict['ret_anch'] + '_foot'
            uPlogExtra(opts,"Reassigning local anchor %s to %s" % 
                       (anch, foot_dict['ret_anch']), 2)

            LocalRaiseAnchor(tag_href, foot_dict['ret_anch'])

    return found



def LocalGenFootDict(opts, tag_href, foot_title,
                     anch, tag_note, tag_cont, ret_anch, number):
    """
    Generate the foot note dictionary
    
    @return: (err - any errors,
              foot_dict - a footnote dictionary)
    """

    foot_dict = {}
    err = ''
    
    if number: # Most wikipedia footnotes are just numbers, but not all...
        tag_href.string = '[' + str(opts['footi']) + ']'
        foot_title = ''
    words, note_list = GenTextWordsFromTags(tag_cont, True)
    if note_list:
        foot_dict = GenTextMakeFootDict(note_list, ret_anch, '', 
            foot_title, 'never')
        foot_dict['orig_anch'] = anch
        opts['footi'] += 1
        if not number:
            tag_href.string = foot_title
        tag_href['href'] = '#' + ret_anch + '_foot'
        tag_note.decompose()
        uPlogExtra(opts, "Reassigning local anchor %s to %s" % (anch, ret_anch), 2)

        LocalRaiseAnchor(tag_href, ret_anch)

    else:
        tag_href.name = 'i'
        err = "Unable to Reassign local anchor %s" % anch

    return err, foot_dict

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
        
        err, foot_dict = LocalGenFootDict(opts, tag_href, foot_title,
                                     anch, tag_note, tag_cont, ret_anch, number)
        
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

        if LocalReuseArticleFnoteCache(opts, tag_href, foot_dict_list):
            psym = 'r'
            r += 1
        else:
            err, foot_dict, tag_parent = LocalReuseArticleFnote(opts, bl, tag_href) 
    
            if not err:            
                foot_dict_list.append(foot_dict)
                psym = 'R'
                r += 1
                if tag_parent:
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

    if tag_parent:
        tag_parent.parent.decompose()

    uPlog(opts, '\nReassigned %d footnotes' % r)
    sys.stdout.flush()
    uPlogExtra(opts, '', 1)

    return foot_dict_list











