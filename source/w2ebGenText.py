
import json

from w2ebUtils import *
from w2ebConstants import *

def GenTextStripSquareBr(opts, par_text):
    """
    @summary: Remove any reference like data surrounded by square brackets [*]
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


def GenTextShortFoot(summ0_in):
    """
    @summary: Generate the text for the short footnote, about MIN_WORDS long.

    @return: A footnote style summary.
    """

    half_minw = MIN_WORDS / 2

    wc = 0 # word count
    summ0_wlist = summ0_in.split(' ')
    summ0 = ''
    for wc in range(0, len(summ0_wlist)):
        word = summ0_wlist[wc]
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
        summ0 = summ0 + ' ' + word

    summ0 = summ0 + ' ' + word

    if summ0[-4:] == '</p>':
        summ0 = summ0[:-4]

    return summ0


def GenTextFootNote(opts, bl):
    """
    @summary: Generate the text for footnotes, both long and short.
    
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
    
    foot_dict ={}
    err = None
    
    words = 0
    
    if not tag:
        err = 'bad_footnote: Can not find class=mw-parser-output in wiki text.'
        return err, foot_dict
    
    summ=[]

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
                    summ = summ + [first_string + '</p>']  # prefix created later
            else:
                par_ind += 1
                summ = summ + ['<p>' + ustr + '</p>']
    
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
        summ = summ + [first_string + '</p>']  # prefix created late
    summ = summ + ['<p></p>']
    
    assert summ[0].count('</p>'), "Need exactly one </p> in first line of footnote"

    summ0 = GenTextShortFoot(summ[0])

    foot_title = opts['footsect_name']

    kindle_fnotes = False #XXX

    num = ' [' + opts['ret_anch'].split('_')[2] +']:'
    
    assert opts['ret_anch'][0] != '#', "Badly formed ret_anch"

    if kindle_fnotes:
        # we think kindle footnotes are activated when the backreference lives in 
        # the same tag as the id....
        shortsumm = '<p>'
        shortsumm += '<a href="' + '#' + opts['ret_anch'] +'"'
        shortsumm += '" id="' + opts['ret_anch'] + '_foot">' + foot_title + num +'</a> '

    else:
        shortsumm = '<p>'
        shortsumm +='<b id="' + opts['ret_anch'] + '_foot">' + foot_title + num +'</b> '
        
        # Kindle is eager to do things wrong... frustrating... 
        #shortsumm += '<a href="' + '#' + opts['ret_anch'] +'">'
        #shortsumm += foot_title + '</a>: '

    shortsumm += summ0
    if not kindle_fnotes:
        # works but is ugly XXX 
        shortsumm += '<a href="' + '#' + opts['ret_anch'] +'"> back</a> /'
        None
    shortsumm += ' <a href="' + '#' + opts['ret_anch'] + '_long">more...</a></p>'
    
    backlinklong  = '<b id="' + opts['ret_anch'] + '_long">' + foot_title + num +'</b> '

    summ[0] = '<p>' + backlinklong + summ[0]

    summ = summ + ['<p><a href="' + '#' + opts['ret_anch'] +'"> back</a> / more @ ']
    summ = summ + ['<a href="' + opts['url'] +'">' + opts['url'] + '</a></p>']  
    summ = summ + ['<br />']

    summ += ['<p><hr width="' + str(int(WMAX * .8)) + '" align="center"></p>']  ## Ok idea, maybe later...

    # basic foot dictionary definition... 
    foot_dict ={}
    foot_dict['short_foot'] = shortsumm
    foot_dict['long_foot'] = summ
    foot_dict['foot_title'] = foot_title
    foot_dict['ret_anch'] = opts['ret_anch']
    foot_dict['msg'] = 0

    return err, foot_dict

def GenTextSummarizeFootNote(opts, bl):
    """
    @summary: Summarize the article represented by bl. Save a representation in the footnote dir.
    
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
    
    opts['footsect_name'] = uCleanChars(opts, opts['footsect_name'])
    
    opts['bodir'] = uCleanChars(opts, opts['bodir'])
        
    uSysMkdir(opts, opts['dcdir'])

    err, bl, section_bname = uGetHtml(opts)
    
    if err:
        return err, []

    uPlog(opts, '==> Fetching Footnote Summary for "' + opts['footsect_name'] + '"')
    uPlog(opts, "Searching:", opts['url'])
    
    opts['section_bname'] = section_bname
    
    err, foot_dict = GenTextSummarizeFootNote(opts, bl)

    assert bool(err) ^ bool(foot_dict), "One of err or foot_dict should be defined" 

    return err, foot_dict


