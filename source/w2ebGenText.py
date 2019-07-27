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
import sys

from w2ebUtils import *
from w2ebConstants import *

from BeautifulSoup import NavigableString
from BeautifulSoup import Tag

import bs4.element

def GenTextStripSquareBr(par_text):
    """
    Remove any reference like data surrounded by square brackets [*]
    """
    
    if not par_text:
        return ''
    
    out_text = par_text
    done = False

    while not done:
        done = True
        ind_l = out_text.find('[')
        ind_r = out_text.find(']')
        
        if ind_l > 0 and ind_r > 0 and ind_l < ind_r:
            out_text = out_text[:ind_l] + out_text[ind_r + 1:]
            done = False

    out_text = ' '.join(out_text.split())  # strips \n \t etc. but not ' '

    return out_text


def GenTextShortFoot(note0_in):
    """
    Generate the text for the short footnote, about MIN_WORDS long.

    @return: A footnote style summary, possibly an incomplete sentence.
    """

    half_minw = MIN_WORDS / 2

    wc = 0 # word count
    note0_wlist = note0_in.split(' ')
    note0 = ''
    for wc in range(0, len(note0_wlist)):
        word = note0_wlist[wc]
        note0 = note0 + ' ' + word
        
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

    #note0 = note0 + ' ' + word

    return note0

def GenTextFootRef(opts, item, yes_i):
    """
    Generate a reference for a footnote.
    
    @param yes_i: Whether the internet 'i' shows up in the text 
    
    @note: References in footnotes themselves can get messy quickly, so we
    only allow them in reused footnotes from the original article. Also we
    suppress them if they point to another footnote since we are in the process
    of renaming all footnote anchors.
    
    @return: (ustr - something to use in place of the anchor tag)
    """



    a_text = uGetTextSafe(item)

    if not item.find('img') and not a_text:
        if not a_text:
            return ''
    
    ustr = '<i>' + uGetTextSafe(item) + '</i>'
    if item.has_attr('href'):
        href = item['href']
        
        if 'http' in href[0:4]:
            if yes_i: # we are done parsing if we allow adding the internet 'i'
    
                label = uGetTextSafe(item)
                if label:
                    ustr = '<a href="%s">%s |i|</a>' % (item['href'], label)
    
            else:
                # break the item by changing its name to 'div', BW would say not to
                item.name = 'div'
                label, sep = GenTexTag2Str(opts, False, True, item, '', '')
    
                ustr = '<a href="%s">%s</a>' % (item['href'], label)
    
        elif '#' in href:
            anch = href.split('#')[1]
            if not 'cite_note' in anch: # probably we can't sort this out here XXX give up
                ustr = '<a href="#%s">%s</a>' % (anch,
                 uGetTextSafe(item))

    return ustr

def GenTexTag2Str(opts, allow_refs, allow_img, tag_pdh, part_string, sep):
    """
    Build up the partial string by appending the rendering of the current tag
    
    @return - words  updated word count
            - part_string  modified partial string
    """
    
    ustr = ''
    tnm = tag_pdh.name

    if not isinstance(tag_pdh, bs4.element.Tag) or not tag_pdh.name:

        ustr = uGetTextSafe(tag_pdh)
        ustr = GenTextStripSquareBr(tag_pdh)

    elif tnm in ['span', 'cite', 'p', 'li', 'td', 'th', 'div' ]:

        for item in tag_pdh:

            part_string, sep = GenTexTag2Str(opts, allow_refs, allow_img, item,
                                                part_string, sep)
            continue

    elif tnm in ['i', 'b', 'u', 'small']: 

            ustr = uGetTextSafe(tag_pdh)
            ustr = '<%s>' % tnm + GenTextStripSquareBr(ustr) + '</%s>' % tnm 

    elif tnm == 'a':

        if not allow_refs:
            ustr = uGetTextSafe(tag_pdh)
        elif allow_refs == 'yes_i':
            ustr = GenTextFootRef(opts, tag_pdh, True)
        elif allow_refs == 'yes_noi':
            ustr = GenTextFootRef(opts, tag_pdh, False)
        else:
            assert 0, "Illegal value for allow_refs:" + str(allow_refs)

    elif tnm == 'img':

        if allow_img:
            ustr = '<center>' + str(tag_pdh) + '</center>'
        else:
            if opts['debug'] >= 2:
                ustr = '{' + os.path.basename(tag_pdh['src']) + '}'

    elif tnm in ['style', 'link', 'sup', 'sub', 'br']:
        # discard these explicitly
        ustr =''
    else:
        uPlogExtra(opts, "Unrecognized tag found during parsing: " +
                    tag_pdh.name, 3)
        
    if ustr:
        part_string = part_string + sep + ustr    # XXX not sure we want sep
        sep = ' '

    return part_string, sep


def GenTextWordsFromTags(opts, head, allow_refs):
    """
    Translate a tag into a list of paragraphs, up to the first heading.
    
    @param allow_refs: Allow references to be included as part of the footnote
    
    @note: For footnotes generated from links to Wikipedia we include the
    Wikipedia reference at the end. For footnotes that are reused from the
    original we attempt to recycle them. XXX 
        
    @note: This function walks through the list of descendents searching for
    at least MIN_WORDS to construct its first paragraph. If the first paragraph
    is less than MIN_WORDS it will merge subsequent paragraphs.
    
    The search stops when NOTE_MAX_PAR paragraphs are reached, or when a major
    heading is reached.
    
    If a major heading is encountered before we have even seen MIN_WORDS, then
    
    
    @return: (words - the total number of words found,
              note_list - a list of paragraphs to make notes or footnotes)
    """

    render_list = ['p', 'a', 'i', 'b', 'u', 'span', 'cite'] # tags to render
    endsearch_list = ['h1','h2']
    search_list = endsearch_list + render_list

    if head.name in ['span', 'cite']:
        list_all = [head]
    else:
        list_all = list(head.find_all(lambda x: x.name in ['h1','h2', 'p']))
    
    words = 0
    note_list = []
    part_string =''
    sep = ''

    for tag_pdh in list_all:

       # print "PPPt=", tag_pdh.name

        if tag_pdh.name in endsearch_list:
            # if we don't have enough words, but are at a major division
            # keep searching... 
            if words < MIN_WORDS:
                continue
            # after finding the TOC normally we are done
            if tag_pdh.has_attr('id') and tag_pdh['id'] == 'toc':
                break

        else:

            part_string, sep = GenTexTag2Str(opts, allow_refs, False, tag_pdh,
                                        part_string, sep)

        # we force the first paragraph to include at least MIN_WORDS
        if tag_pdh.name == 'p':
            if len(note_list) == 0 and part_string.count(' ') < MIN_WORDS:
                continue

            note_list += [part_string]
            words += part_string.count(' ')
            part_string = ''
            sep = ''
    
        if len(note_list) > NOTE_MAX_PAR:
            # stop so we don't read a whole article
            break
    
    if part_string:
        words += part_string.count(' ')
        note_list += [part_string]

    return words, note_list

#
# Kindle has a footnote feature where the footnote pops up on the screen instead
# of behaving like a link. The feature does not work consistently. Sometimes
# there is no pop-up, at other times the popup is there, but it includes too many
# footnotes.
#
# Popups seem to be triggered by references that include backlinks. Our backlink
# is intentionally separated from our anchor to disable this feature. 
#


def GenTextLongAndShort(note_list, id_anch, url, foot_title,
                            notes, note0, num):
    """
    Footnotes include both a long and short version, generate both here
    
    @return: (shortnote - the short version, aka a footnote,
              note_list - the long version, a list of paragraphs)
    """

    shortnote = '<p>'
    shortnote += '<b id="' + id_anch + '_foot">' + foot_title + num + '</b> '
    shortnote += note0
    #shortnote += '<a href="' + '#' + id_anch + '"> back</a>'
    shortnote += W2EB_BLM

    if notes == 'never':
        if url:
            shortnote += ' / more @ <a href="' + url + '">' + url + '</a></p>'
        else:
            shortnote += '</p>'
        long_note_list = []

    else:
        shortnote += ' / <a href="' + '#' + id_anch + '_long">more...</a></p>'

        backlinklong = '<b id="' + id_anch + '_long">' + foot_title + num + '</b> '
        long_note_list = ['<p>' + backlinklong + note_list[0] + '</p>']
        
        for note in note_list[1:]:
            long_note_list += ['<p>' + note + '</p>']

        #long_note_list += ['<p><a href="' + '#' + id_anch + '"> back</a>']
        long_note_list += ['<p>' + W2EB_BLM]
        if url:
            long_note_list += [' / more @ <a href="' + url + '">' + url + '</a></p>']
        else:
            long_note_list += ['</p>']

        long_note_list += ['<br />']
        long_note_list += ['<p><hr width="' + str(int(WMAX * .8)) + '" align="center"></p>'] ## Ok idea, maybe later...

    return shortnote, long_note_list


def GenTextMakeFootDict(opts, note_list, url, foot_title, notes):
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
    

    note0 = GenTextShortFoot(note_list[0])


    foot_dict = {}

    uGenRetAnch(opts, foot_dict, foot_title)

    num = ' [' + foot_dict['id_anch'].split('_')[2] + ']:'

    shortnote, note_list = GenTextLongAndShort(note_list, foot_dict['id_anch'],
                                url, foot_title, notes, note0, num)

    # basic foot dictionary definition...

    foot_dict['short_foot'] = shortnote
    foot_dict['long_foot'] = note_list
    foot_dict['foot_title'] = foot_title
    foot_dict['orig_anch'] = ''
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
                        - 'id_anch' return anchor for the footnote
                        - 'msg' whether a debug message has been generated)
    """
     
    # seems to be the single wikimedia tag defining text content
    #    
    # sort of, found some cases where this wasn't true,
    # for example: https://en.wikibooks.org/wiki/Special:Categories
    # Lets erase the output file, treat it as a bust
    
    head = bl.find('div', class_='mw-parser-output')
    
    err = ''
        
    if not head:
        err = 'bad_footnote: Can not find class=mw-parser-output in wiki text.'
        return err, {}
    
    words, note_list = GenTextWordsFromTags(opts, head, False)
    
    if words < MIN_WORDS:

        err = 'bad_footnote: Did not find enough text.'
        uPlog(opts, 'Short footnote. Found %d words, need at least %d words.' %
             (words, MIN_WORDS))
        if words > 0:        
            uPlog(opts, '\n', note_list[0], '\n')
        return err, None
    
    notes = opts['notes']
    foot_title = opts['footsect_name']
    url = opts['url']
    
    foot_dict = GenTextMakeFootDict(opts, note_list, url, foot_title, notes)

    return err, foot_dict


def GenTextSummarizeFootNote(opts, bl):
    """
    Summarize the article represented by bl. Save a representation in the footnote dir.
    
    @return (err, or a dictionary of footnote items)
    """
    
    err, foot_dict = GenTextFootNote(opts, bl)
    if foot_dict:
        fp = open(opts['base_bodir'] + '/footnotes/' + foot_dict['id_anch'] + '.json', 'w')
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


