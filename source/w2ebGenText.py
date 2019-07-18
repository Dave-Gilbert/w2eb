"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

import json

from w2ebUtils import *
from w2ebConstants import *

def GenTextStripSquareBr(opts, par_text):
    """
    Remove any reference like data surrounded by square brackets [*]
    """
    
    par_text = par_text
    
    if not par_text:
        return ''
    par_text = par_text.strip()
    if not par_text:
        return ''
    par_text = ' '.join(par_text.split())  # strips \n \t etc. but not ' '

    if not par_text:
        return ''
    # There is probably a better way to do this, but for now
    # just explicitly kill the first 50 numerical references.
    for i in range(0,50):
        par_text = par_text.replace('[' + str(i) + ']', '')

        
    return par_text


def GenTextShortFoot(note0_in):
    """
    Generate the text for the short footnote, about MIN_WORDS long.

    @return: A footnote style summary.
    """

    half_minw = MIN_WORDS / 2

    wc = 0 # word count
    note0_wlist = note0_in.split(' ')
    note0 = ''
    for wc in range(0, len(note0_wlist)):
        word = note0_wlist[wc]
        if word[-4:] == '</p>':
            break 
        if word[-1:] in Punc1 and wc > 2 * half_minw:
            if word[-3:-2].isalpha():  # avoid single letter initials h.p. lovercraft
                break
        if word[-1:] in Punc2 and wc > 4 * half_minw:
            break
        if word[-1:] in Punc3 and wc > 6 * half_minw:
            break
        if word[-1:] in Punc4 and wc > 8 * half_minw:
            word = word[:-1]
            break
        if wc > 8 * half_minw:
    #        print "found foo_max"
            break
        note0 = note0 + ' ' + word

    note0 = note0 + ' ' + word

    if note0[-4:] == '</p>':
        note0 = note0[:-4]

    return note0



def GetTextMakeFootDict(opts, note):
    """
    Construct the foot dictionary from the raw text summary. Add backlink, number etc.
    
    @return: foot_dict - a structure with several standard entries
    """
    # Kindle has a footnote feature where it creates a small box on top of the
    # text where the footnote appears, however, it doesn't work consistently.
    # A boolean is included to enable it one day, but for not it simply doesn't
    # work. The backlink needs to be kept separate from the id to disable it.
    # keeping them together only sometimes enables it, and often the Kindle can't
    # seem to find the end of the footnote.
    
    kindle_fnotes = False
    
    assert note[0].count('</p>'), "Need exactly one </p> in first line of footnote"
    assert not kindle_fnotes, "Kindle style footnotes are not supported"

    note0 = GenTextShortFoot(note[0])
    foot_title = opts['footsect_name']

    num = ' [' + opts['ret_anch'].split('_')[2] + ']:'
    assert opts['ret_anch'][0] != '#', "Badly formed ret_anch"

    if kindle_fnotes:
        # we think kindle footnotes are activated when the backreference lives in
        # the same tag as the id....
        shortnote = '<p>'
        shortnote += '<a href="' + '#' + opts['ret_anch'] + '"'
        shortnote += '" id="' + opts['ret_anch'] + '_foot">' + foot_title + num + '</a> '
    else:
        shortnote = '<p>'
        shortnote += '<b id="' + opts['ret_anch'] + '_foot">' + foot_title + num + '</b> '
        # Kindle is eager to do things wrong... frustrating...
        #shortnote += '<a href="' + '#' + opts['ret_anch'] +'">'
        #shortnote += foot_title + '</a>: '
    shortnote += note0
    if not kindle_fnotes:
        # works but is ugly XXX
        shortnote += '<a href="' + '#' + opts['ret_anch'] + '"> back</a>  / '
        None
    
    if opts['notes'] == 'never':
        shortnote += ' more @ <a href="' + opts['url'] + '">' + opts['url'] + '</a></p>'
        note = []
    else:
        shortnote += ' <a href="' + '#' + opts['ret_anch'] + '_long">more...</a></p>'
        backlinklong = '<b id="' + opts['ret_anch'] + '_long">' + foot_title + num + '</b> '
        note[0] = '<p>' + backlinklong + note[0]
        note = note + ['<p><a href="' + '#' + opts['ret_anch'] + '"> back</a> /  more @ ']
        note = note + ['<a href="' + opts['url'] + '">' + opts['url'] + '</a></p>']
        note = note + ['<br />']
        note += ['<p><hr width="' + str(int(WMAX * .8)) + '" align="center"></p>'] ## Ok idea, maybe later...

    # basic foot dictionary definition...
    foot_dict = {}
    foot_dict['short_foot'] = shortnote
    foot_dict['long_foot'] = note
    foot_dict['foot_title'] = foot_title
    foot_dict['ret_anch'] = opts['ret_anch']
    foot_dict['msg'] = 0
    
    return foot_dict

def GenTextFootNote(opts, bl):
    """
    Generate the text for footnotes, both long and short.
    
    @return: (err - any error,
              foot_dict - a structure with 4 fields
                        - 'short_foot' short versions of a footnote
                        - 'long_foot' long versions of a footnote
                        - 'foot_title' name of the footnote, usually the link
                        - 'ret_anch' return anchor for the footnote
                        - 'msg' whether a debug message has been generated)
    """
     
    # seems to be the single wikimedia tag defining text content
    #    
    # sort of, found some cases where this wasn't true,
    # for example: https://en.wikibooks.org/wiki/Special:Categories
    # Lets erase the output file, treat it as a bust
    
    tag = bl.find('div', class_='mw-parser-output')
    
    err = None
    
    words = 0
    
    if not tag:
        err = 'bad_footnote: Can not find class=mw-parser-output in wiki text.'
        return err, {}
    
    note = []

    max_par = NOTE_MAX_PAR
    par_ind = 0
    
    first_par = True
    first_string =''
    for item in tag:

        tag = item.name

        if tag in ['div', 'h1', 'h2']:
            if item.has_attr('id') and item['id'] == 'toc':
                # usually a full footnote can be found before the wikipedia toc,
                # sometimes the footnote isn't enough though. If we have found
                # the toc keep reading, at least 5 paragraphs.
                
                if words < MIN_WORDS:
                    # don't quit just yet. Keep going
                    # and see if we can find a little more text
                    # after the toc, but keep it limited
                    max_par = NOTE_MAX_PAR / 2
                else:           
                    break
        
        elif tag in ['p', 'b', 'i', 'u', 'pre', 'code', 'tt', 'center']:

            ustr = item.get_text()
            ustr = GenTextStripSquareBr(opts, ustr)
            words += ustr.count(' ')
            first_string = first_string + ' ' + ustr
                    
            if first_par:
                if words < MIN_WORDS:   # we need at least MIN_WORDS before paragraph 1 ends
                    first_string.replace('</p>',' ')
                    continue
                else:
                    first_par = False
                    note = note + [first_string + '</p>']  # prefix created later
            else:
                par_ind += 1
                note = note + ['<p>' + ustr + '</p>']
    
        if par_ind > max_par:
            # stop so we don't read a whole article
            break
    
    if words < MIN_WORDS:

        err = 'bad_footnote: Did not find enough text.'
        uPlog(opts, 'Short footnote. Found %d words, need at least %d words.' %
             (words, MIN_WORDS))
        if words > 0:        
            uPlog(opts, '\n', first_string, '\n')
        return err, None

    if first_par:
        note = note + [first_string + '</p>']  # prefix created late
    note = note + ['<p></p>']
    
    foot_dict = GetTextMakeFootDict(opts, note)

    return err, foot_dict

def GenTextSummarizeFootNote(opts, bl):
    """
    Summarize the article represented by bl. Save a representation in the footnote dir.
    
    @return (err, or a dictionary of footnote items)
    """
    
    err, foot_dict = GenTextFootNote(opts, bl)
    if foot_dict:
        fp = open(opts['base_bodir'] + '/footnotes/' + opts['ret_anch'] + '.json', 'w')
        if fp:
            json.dump(foot_dict, fp)
            fp.close()
        else:
            uPlog(opts, "Warning: unable to save footnote in cache, proceeding anyway")
# Not being able to cache a file should maybe create just a warning.

    return err, foot_dict

def GenTextGetFootNote(opts):
    
    st_time = time.time()
    foot_dict = {}
    
    opts['footsect_name'] = opts['footsect_name']
            
    uSysMkdir(opts, opts['dcdir'])

    err, bl, section_bname = uGetHtml(opts)
    
    if err:
        return err, []

    uPlogExtra(opts, '==> Fetching Footnote Summary for "' + opts['footsect_name'] + '"', 3)
    uPlogExtra(opts, "Searching:" + opts['url'], 3)
    
    opts['section_bname'] = section_bname
    
    err, foot_dict = GenTextSummarizeFootNote(opts, bl)

    assert bool(err) ^ bool(foot_dict), "One of err or foot_dict should be defined" 

    return err, foot_dict


