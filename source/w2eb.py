#!/usr/bin/python

import unicodedata
import time
import sys
import os
import getopt

import urllib

# import warnings

import traceback
import json
from shutil import copyfile
# import BeautifulSoup
from bs4 import BeautifulSoup
from bs4 import NavigableString
from bs4 import Comment
from _ast import Or


from w2ebFootNotes import FootNotes
from w2ebUtils import *

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

BASE_DIR = '/home/gilbert/Projects_Recent/wiki_books'

IMAGE_PIC = ['.jpg', '.JPG', 'jpeg', 'JPEG']
IMAGE_FIG = ['.gif', '.GIF', '.png', '.PNG']
IMAGE_SVG = ['.svg', '.SVG']
SUFFIX_OT = ['.ico', '.php', '.pdf', '.PDF']

#
# There are a few bad images that we see regularly... 
#
IMAGE_AVOID = ['Special:CentralAutoLogin']

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

def get_text_safe(curr):
    
#     text_out = ''
#     if isinstance(curr, NavigableString):
#         text_out = str(curr).strip()
#     else:
#         if curr:
#             try:
#                 if len(curr.contents) == 1:
#                     text_out = curr.string
#                 else:
#                     text_out = str(curr.get_text())
#             except Exception as e:
#                 print len(curr.contents)
#                 print "XXX caught get_text exception", e
#                 print curr
#             
#     return text_out
    
    # XXX get_text() and several other methods are failing
    # on these tags with the error:
    #
    # File "python2.7/site-packages/bs4/element.py", line 1339, in descendants
    # current = current.next_element
    # AttributeError: 'NoneType' object has no attribute 'next_element'
    #
    # This makes me believe that I have broken the tag tree somehow.
    # I have been destroying a lot of tags, perhaps that is the problem
    # and I need to somehow do that more cleanly. Documentation for
    # destroy does say that it removes the tag, then destroys it... not sure.
    # I tried explicitly extracting tags before destroying them, that didn't work... 
    
    curr_str = ''
    
    try:
        for string in curr.strings:
            try:
                curr_str += string
            except:        
                None
    except:
        if curr_str == '':
            try:
                curr_str = curr.string
            except:
                # I am confused, and don't get this object.
                None

    return curr_str.strip()



def clean(opts):
    
    del_msg = "XXXX What are we trying to delete? Everything? THIS IS A BAD BUG...XXXX"
    assert len(opts['bodir']) > 10, del_msg
    assert len(opts['dcdir']) > 10, del_msg

    #
    # If we are running on a subarticle don't chatter about cleaning up
    # directories, we will already have this message in the parent
    #

    cwd = os.getcwd()
    
    cwd_msg = "\n\nUnable to clean the current working directory.\n Try cd ..\n"
    
    if opts['clean_book']:
        assert not opts['bodir'] in cwd, cwd_msg 
        uSysCmd(opts, 'rm -r "' + opts['bodir'] + '"', False)

    uSysMkdir(opts, opts['bodir'])
    if opts['parent'] == '':
        uPlog(opts, '')
        if opts['clean_book']:
            uPlog(opts, "Removing all generated htmlfiles, footnotes, images, and equations.")

    if opts['clean_cache']:

        if opts['parent'] == '':
            assert not opts['dcdir'] in cwd, cwd_msg
            uSysCmd(opts, "rm -r " + opts['dcdir'] , False)
            uPlog(opts, "Removing all data previously downloaded from the Internet")
    
    if opts['clean_html']:
        if opts['parent'] == '':
            uSysCmd(opts, 'find "' + opts['bodir'] +'" -name \*.html -exec rm \{\} \;' , False)
            uPlog(opts, "Removing generated html files, and failed urls from the cache.")
    
    uSysMkdir(opts, opts['bodir'] + '/images')
    uSysMkdir(opts, opts['bodir'] + '/footnotes')

    uSysMkdir(opts, opts['dcdir'])
    uSysMkdir(opts, opts['dcdir'] + '/images')
    uSysMkdir(opts, opts['dcdir'] + '/footnotes')


def get_html(opts):
    """
    @param opts
    
    Gets whatever get_html will collect for a url in opts and 
    returns the basename of that file for use as a reference.
    
    Extract the htmlsoup and save the .html file in the cache
    """

    bl = None
    section_bname = ''
    err = ''

    htmlfile = uGet1HtmlFile(opts, opts['dcdir'], False)
    if htmlfile:
        # uPlog(opts, "cache hit found", htmlfile
        opts['chits'] = opts['chits'] + 1
    else:
    
        wgopts = WGET_OPTS + ' -o "' + opts['dcdir'] + '/wget_log.txt"'
        wgopts = wgopts + ' --convert-links --no-directories --directory-prefix="' + opts['dcdir'] + '/"'

        # the url may not exists, so always be tentative with at least this wget
        if opts['wikidown']:
            err = 'wikidown: -w disables wget fetches to wikipedia and relies on cached data'
            opts['wikidown'] += 1
        else:
            err = uSysCmd(opts, '/usr/bin/wget ' + wgopts + ' "' + 
                      opts['url'] + '"', False)
            if not err:
                opts['wgets'] += 1
                uPlogExtra(opts, "wget: "+ opts['url'], 3)
                uPlogFile(opts, opts['dcdir'] + '/wget_log.txt', 3)
            else:
                uPlogExtra(opts, "XXX Failed: wget "+ opts['url'], 1)
                uPlogFile(opts, opts['dcdir'] + '/wget_log.txt', 1)


    if not err:
        htmlfile = uGet1HtmlFile(opts, opts['dcdir'], False)
        if not htmlfile:
            err = 'URL is okay, but could not find .html file. See ' + opts['url']

    if not err and htmlfile:
        section_bname = urllib.unquote(uCleanChars(opts, os.path.basename(htmlfile)))

        assert htmlfile
        with open(htmlfile) as fp:
            bl = BeautifulSoup(fp, "html.parser")

    if err:
        uPlog(opts, "No data for", opts['url'])
        uPlog(opts, err)
        uPlog(opts, "Verify that URL exists")
        uPlog(opts, '')
        err = 'url_failed: ' + err

    return [err, bl, section_bname]


def get_image(opts, url, image_file):
    """
    @summary:  Fetch image file from "url" save to output file name "image_file"
    """
            
    err = ''
    
    if opts['no_images']:
        return 1
    
    ind = url.find('://')
    fname = url[ind +3:]
#    fname = urllib.unquote(url[ind +3:])  # XXX these sometimes have unreadable characters in them

    image_dir = os.path.dirname(image_file)

    if os.path.exists(opts['dcdir'] + '/images/' + fname):
        #uPlog(opts, "cache hit found", opts['dcdir'] + '/images/' + fname

        opts['chits'] = opts['chits'] + 1
    else:
        log_file = '"' + opts['dcdir'] + '/images/wget_log.txt"'
        wgopts = WGET_OPTS + ' -o ' + log_file    
        wgopts = wgopts + ' --directory-prefix="' + opts['dcdir'] + '"/images '

        if opts['wikidown']:
            err = 'wikidown: -w disables wget fetches to wikipedia and relies on cached data'
            opts['wikidown'] += 1
        else:        

            err = uSysCmd(opts, '/usr/bin/wget ' + wgopts + ' "' + url + '"', 
                          opts['debug'])
            
            if not err:
                uPlogExtra(opts, "wget: " + url, 3)
                opts['wgets'] += 1
            else:
                uPlogExtra(opts, "Failed: wget " + url, 2)
                uPlogFile(opts, opts['dcdir'] + '/images/wget_log.txt', 2)

    if not err:
        uSysMkdir(opts, opts['bodir'] + '/' + image_dir)
        
        try:
            src_f = opts['dcdir'] + '/images/' + fname
            srcfile = urllib.unquote(src_f)
        ## urllib generates a noisy warning 
        
        #         with warnings.catch_warnings():
        #             warnings.simplefilter("ignore")
        #             srcfile = urllib.quote(src_f) # has some messy warnings. They don't seem important.
        
        #        srcfile = urllib.quote(src_f)
            copyfile(srcfile, opts['bodir'] + '/' + image_file)
        except Exception as e:
            uPlogFile(opts, opts['dcdir'] + '/images/wget_log.txt', 1)
            uPlogExtra(opts, "Exception: " + uCleanChars(opts, str(e)), 1)
            err = 'Image name has messy control characters ' + uCleanChars(opts, fname)
            # Sometimes wget garbles the dowloaded file name in a way that we can't guesss.
            # The right fix involves testing for messy strings prior to
            # download, and then specifying some safe version of the string later on...

    if not err and not os.path.exists(opts['bodir'] + '/' + image_file ):
        err = 'Missing file: ' + opts['bodir'] + '/' + image_file
    return err

def substr_bt(Str, pre, post):
    
    rval =""
    ind2 = -1
    
    ind = Str.find(pre, 0)
    if ind >= 0 and post != '$':
        ind2 = Str.find(post, ind + len(pre))
        if ind2 >= 0:
            rval = Str[ind + len(pre): ind2]        # +1?
    elif ind >= 0:
        rval = Str[ind + len(pre):] # +1?

    return rval

def usage(err):

    print """
wiki_get.py, A script for fetching html versions of Wikibooks."""

    if not err:
        print """
    usage:  wiki_get.py  [opts] [-u <URL>] [-b <book>] 
        
        -c        Erase all .html files and retry URLs that previously failed.
        -C        Erase all generated files, including .html, images, and footnotes.
        -K        Clean generated files and network cache. Redownload everything.
                    Without c, C, or K, a normal run will rewrite root html only.
        -E        Export book to epub. Uses calibre for conversion.
        
        -n        No images 
        -B        Convert color images to black and white, should reduce file sizes.
        -P        Convert all .svg images to .png. Older e-readers may not support .svg.
                    Wikipedia provides math equations in .svg format, converting them takes time.
        -s        Use .svg for non-math figures. Svg figures with transparent zones 
                    don't render correctly on the kindle. Default is to render them.
        -u <url>  Url to use as the base of the ebook. If -b is not supplied the basename
                    of the url will be used to generate the bookname.
        -b <nm>   The name of the e-book. Try to guess a wikipedia style url based on
                    the bookname if -u is not supplied. 
              
        -d <#>    depth, 0 for no subarticles, 2 for default.
        -S <typ>  Section type. Determines whether a link is treated as a subsction or not.
                  <typ> can be one of:
                  bookurl  - subsection url has book url as a substring
                  bookname - subsection url has book name as a substring  < default>
                  bookword  - subsection url has at least one 4 letter word from book name as substring
        
        -D <#>    Debug level. 0 = none, 1 = footnote only, 2 = failure only, 3 = all.
        -w        wiki down, rely on cache instead of wget (debugging...)
        -h        this message
"""

    if err:
        print '\n' + err
        print '\nUse "-h" for help'

    print ''
    
    sys.exit(1)
        
    assert 0, "Failed to exit"


def GetOptions():
    
    try:
        op, args = getopt.getopt(sys.argv[1:], 'Eu:b:cCKd:D:nwbphPsS:')
    except:
        usage("Error: unrecognized command line options: " +
              " ".join(sys.argv[1:]));

    if len(args) > 0:
        usage('Trailing Options Not Processed:\n' + str(args))

    clean_html = False
    clean_book = False
    clean_cache = False
    wikidown = 0
    export = False 
    
    url = ""
    booknm = ''
    argc = 1
    depth = 2
    no_images = False
    wspider = 0
    bw_images = False
    svg2png = False
    svgfigs = False
    debug = 2
    stype = 'bookname'
    
    for o, a in op:
        argc += 1
        if o == '-u':
            url = a
        elif o == '-b':
            booknm = a
        elif o == '-c':
            clean_html = True 
        elif o == '-C':
            clean_html = True
            clean_book = True
        elif o == '-B':
            bw_images = True
        elif o == '-P':
            svg2png = True
        elif o == '-s':
            svgfigs = True
        elif o == '-S':
            if a == 'bookurl':
                stype = 'url'
            elif a == 'bookname':
                stype = 'bookname'
            elif a == 'bookword':
                stype = 'bookword'
            else:
                usage('Unrecognized option for -S = %s. Use -h to get a list of valid options' % a)
            
        elif o == '-K':
            clean_html = True
            clean_book = True
            clean_cache = True
        elif o == '-d':
            try:
                depth = int(a)
            except:
                usage('-d requires a numeric argument')
        elif o == '-D':
            try:
                debug = int(a)
            except:
                usage('-D requires a numeric argument')
        elif o == '-n':
            no_images = True
        elif o == '-w':
            wikidown = 1
        elif o == '-E':
            export = True
        elif o == '-u':
            usage('')
        else:
            usage('Option "%s" not supported for arg "%s"' % (o,a))

    if svg2png and svgfigs:
        usage('Cannot combine -P and -s')

    if not booknm and url:
        booknm = substr_bt(url,'title=','/')
        if not booknm:
            booknm = substr_bt(url,'/wiki/','/Print_version')
        if not booknm:
            booknm = substr_bt(url,'/wiki/','/Print_Version')
        if not booknm:
            booknm = substr_bt(url,'/wiki/','/print_Version')
    
    if not booknm:
        usage('Need a book name. Either use an explicit "-b" or pick a different url.')

    # we can't do much without a bookname
    
    bodir = BASE_DIR + '/book/' + booknm
    dcdir = BASE_DIR + '/dcache/' + booknm
    logfile = bodir + '/' + 'wiki_log.txt'
    
    if os.path.exists(logfile):
        os.remove(logfile)

    # raise exit
    if wikidown and booknm and not url:
        url = 'https://en.wikibooks.org/wiki/' + booknm + '/Print_version'
        wikidown += 1
        # usage("Using -w requires -u")

    if wikidown and clean_cache:
        usage("Using -w relies on having cache data. Do not combine with -K")

    #if we get this far try to make the output directory so we can log information
    
    if booknm and not url:
        check = "wget  -l 0 -t 3 -T 5 -o /dev/null --spider "  
        urlp = "https://en.wikibooks.org/wiki/" + booknm     
        urlw = "https://en.wikipedia.org/wiki/" + booknm     

        # not sure why there are 3 kinds of 'print_versions...'
        # but it seems to always be one of these
        
        lf= {'logfile': logfile, 'debug': debug}
        for url in [urlp + "/Print_Version", urlp + "/Print_version",
                    urlp + "/print_version", urlp, urlw]:

                if os.path.exists(bodir):
                    uPlogExtra(lf, "Guessing url: " + url, 3)
                err = os.system(check + url)
                wspider += 1
                
                if not err:
                    if os.path.exists(bodir):
                        uPlogExtra(lf, "Resolved url", 3)
                    break
                    
        if err:
            usage('Unable to guess url from book name. Maybe there is no "Print_Version"\nUse -u instead.')
                
    if url == "":
        usage("Use -u to define <URL>, or -b to define <Book>")  
    
    opts = {'url':url,                  # url to download book from
            'footsect_name': booknm,    # footnote or section name, initially the same as booknm
            'booknm': booknm,           # book name, may include '/' for sub-articles
            'stype': stype,
            'clean_html': clean_html,   # find and erase all the html files, leave images, dirs etc.
            'clean_book': clean_book,   # erase the book output directory, images dirs and all
            'clean_cache': clean_cache, # erase the cach directory for the book, forces redownload
            'depth': depth,             # 0 = no sub articles, 1 = footnote sub article
            'footnote': False,           # whether this is a footnote, never set from CLI
            'bodir': bodir,             # book output directory
            'dcdir': dcdir,             # download cache directory
            'no_images': no_images,     # suppress images
            'bw_images': bw_images,     # black and white images
            'svg2png': svg2png,         # convert all .svg files to .png files
            'svgfigs': svgfigs,         # use .svg for figures rather than .png
            'logfile': logfile,
            'chits': 0,                 # number of cache hits
            'wgets': wspider,           # number of times we fetched from the web
            'export': export,
            'debug': debug,
            'wikidown': wikidown}        # Don't use wget to access wikipedia, - slow or down
    
    # start with a fresh log file only if this is a manual invokatio
    
    return opts


def str_smh(secs):
    
    if secs < 180:
        retval = "%3d secs" % int(secs)
    elif secs < 7200:
        retval = "%3d mins" % int((30 + secs)/60)
    else:
        retval = "%2d hours" % int(secs/3600)
    
    return retval

def print_time_left(opts, perc, secs):

    if secs < 1:
        secs = 1
                
    uPlogNr(opts, "\n%2s %% %s left" % (perc, str_smh(secs)),">")

def print_progress(opts, st_time, im_tot, im_all, p_total_est_time):
    
    pdone = int(100 * im_tot / im_all)                
    t2 = time.time()
    
    if im_tot == 0:
        total_est_time = p_total_est_time
    else:
        total_est_time = ((t2 - st_time) * im_all) / im_tot
        total_est_time = (total_est_time + p_total_est_time) / 2
        
    if im_tot > 60: 
        p_total_est_time = total_est_time # smoothing factor
        
    tleft = int((total_est_time - (t2 - st_time)))
    
    print_time_left(opts, pdone, tleft)
        
    return p_total_est_time            





Punc1 = ['.','?','!']           # good way to end a sentence
Punc2 = [',', ':', ';']        # less good
Punc3 = [')',']','}','>']       # ...
Punc4 = ['@','#','$','/','\\', '%','^','&','*','(','[','{','<']


def ShortFoot(summ0_in):
    """
    This function is almost the same as the next one, can they be merged?
    Not sure...
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


def tag_hasid(tag):
    
    if tag and tag.has_attr('id'):
        return True
    
    return False

TAG_FMSG = 'Fixing Tags:'

def fix_easy_prog(opts, ma):
    """
    @summary: progress indicator for tag fixing. With big HTML files it can take a bit
    """

    if opts['clen'] > 68:
        uPlogNr(opts,'\n' + ' ' * len(TAG_FMSG))
        opts['clen'] = len(TAG_FMSG) + 1

    uPlogNr(opts, ma)
    sys.stdout.flush()

    opts['clen'] += len(ma) + 1

    
def is_comment(tag):
    if isinstance(tag, Comment):
        return True
    return False

def fix_easy_tags(opts, bl, ipath):
    """
    Simple modifications to base wiki pages
    
    wikipedia recommends downloading portions of its database
    rather than scraping .html files. This function is effectively
    simplifying the pages so they are managable, and that might
    have been avoided by just downloading text directly as suggested.
    
    Perhaps another version will do as suggested... 
    
    B.T.W. this function is kind of slow...
    """
    # make all links to this book relative
    bname = opts['section_bname']
    footsect_name = opts['footsect_name']
    ref = 'https://en.wikibooks.org/wiki/' + footsect_name + '/'

    allanch={}
    
    fname = ref + bname
    opts['clen'] = 0

    uPlogNr(opts, '\n')
    fix_easy_prog(opts, TAG_FMSG)

    # /for tag in bl.findall()
    i = 0;
    for anch in bl.find_all('a', href = True):
                
        anch['href'] = anch['href'].replace(fname,'')
                
        if anch['href'][0:len(ref)] == ref:
            lanch = anch['href'][len(ref):]
            
            if not lanch in allanch:
                i += 1
                if i % 2 == 0:
                    fix_easy_prog(opts,lanch[0:2])
                
                if bl.find('span', id=lanch):
                    allanch[lanch] = True
                else:
                    allanch[lanch] = False
            
            if allanch[lanch]:
                # lanch refers to local anchor in this document
                # simplify it
                anch['href'] = anch['href'].replace(ref,'#') 

    # Kindle always seems to navigate to the point right after a heading
    # which is a bother. Fix this by moving the id from span to span's parent.
    # get rid of the span tag while we are at it. It is noisy and not that helpful    

    fix_easy_prog(opts,'id')

    for tag in bl.find_all('span', class_="mw-headline"):
        if tag.has_attr('id'):
            tag.parent['id'] = tag['id']
            del tag['id']
            tag.parent.contents.extend(tag.contents)
            tag.extract() # we cant decompose since we still refer to data in tag

    
    # remove a lot of the noisy / non-functional elements.

    fix_easy_prog(opts,'sc')
                                      
#   for tag_scr in bl.html.head.find_all('script'):
    for tag_scr in bl.find_all('script'):
        tag_scr.decompose()

    fix_easy_prog(opts,'li')

    for tag in bl.html.head.find_all('link', href=True):
        tag.decompose()

    fix_easy_prog(opts,'me')

    for tag in bl.html.head.find_all('meta'):
        tag.decompose()

    fix_easy_prog(opts,'sp')
    
    for edit in bl.find_all('span', class_="mw-editsection"):
        edit.decompose()

    # if the only item for a tag is string based contents
    # then access it via '.string'        

    fix_easy_prog(opts,'ti')

    bl.head.title.string = bl.head.title.string.replace(
        '/Print version - Wikibooks, open books for an open world','')

    # these look really ugly 
    fix_easy_prog(opts,'jl')

    for item in bl.find_all('a', class_="mw-jump-link"):
        item.decompose()

    # these look really ugly, no print suggests they are only for the web
    fix_easy_prog(opts,'np')

    for item in bl.find_all('div', class_="noprint"):
        item.decompose()

    fix_easy_prog(opts,'na')

    # these look really ugly, no print suggests they are only for the web
    for item in bl.find_all('div', id='mw-navigation'):
        item.decompose()
        
    # some of this material just looks bad in an .epub

    fix_easy_prog(opts,'ta')
    
    for tag in bl.find_all('table'):
    
        if tag.find('a href="https://en.wikibooks.org/wiki/File:Printer.svg"'):
            tag.decompose()

    fix_easy_prog(opts,'di')

    for tag in bl.find_all('div', id='contentSub'):
        tag.decompose()

    fix_easy_prog(opts,'td')
       
    for tag in bl.find_all('td', class_='mbox-text'):
        tag.decompose()

    # ugly things near the end of the doc

    fix_easy_prog(opts,'ft')

    for tag in bl.find_all('div', id='footer'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()

    fix_easy_prog(opts,'pf')

    for tag in bl.find_all('div', class_='printfooter'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()

    fix_easy_prog(opts,'cl')

    for tag in bl.find_all('div', class_='catlinks'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()

    fix_easy_prog(opts,'hi')

    for tag in bl.find_all('div', id='mw-hidden-catlinks'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()
            
    # have found some messy stuff at the end of documents that starts with
    # a tag of the class hiddenStructure. Blow it away

    fix_easy_prog(opts,'hi')
    
    for tag in bl.find_all('div', class_='hiddenStructure'):
        # remove all to the end.
        tnext = tag
        curr = tag
         
        while tnext:
            curr = tnext
            tnext = curr.next_sibling
            if isinstance(curr, NavigableString):
                continue
            curr.decompose()

#    from the web:
#
#    div = soup.find('div', class_='foo')
#    for element in div(text=lambda text: isinstance(text, Comment)):
#        element.extract()


    for comment in bl.findAll(text=lambda text:isinstance(text, Comment)):
        comment.extract()
    # why do we need the entire GNU license

    fix_easy_prog(opts,'gn')

    gnu = bl.find('h1', id='GNU_Free_Documentation_License')
    if not gnu:
        gnu = bl.find('h2', id='GNU_Free_Documentation_License')
    if not gnu:
        gnu = bl.find('h3', id='GNU_Free_Documentation_License')
    
    if gnu:
        gnu.name = 'h3'
        tag = bl.new_tag('p')
        tag.string="""Permission is granted to copy, distribute and/or modify this document
  under the terms of the GNU Free Documentation License, Version 1.3
  or any later version published by the Free Software Foundation;
  with no Invariant Sections, no Front-Cover Texts, and no Back-Cover
  Texts.  A copy of the license is included in the section entitled ``GNU
  Free Documentation License.``see http://www.gnu.org/copyleft/"""

        gnu.insert_after(tag)

    
        tag = tag.next_sibling
        tnext = tag
        curr = tag
         
        while tnext:
            curr = tnext
            tnext = curr.next_sibling
            if isinstance(curr, NavigableString):
                continue
            curr.decompose()
            
    fix_easy_prog(opts,'\n')  # done... 
                

def MergeSectUniq(opts, sect_label_href_list, sect_label_href_list2):
    """
    @summary: Merge two section lists, include unique items only
    """
    items_merged = 0
    if sect_label_href_list:
        for item in sect_label_href_list2:
            if not FindSectHref(opts, item['html_file'], sect_label_href_list):
                items_merged += 1
                sect_label_href_list.append(item)

    return items_merged


def MergeFootUniq(foot_dict_list, foot_dict_list2):
    """
    @summary: Merge two footnote lists, include unique items only
    """
    items_merged = 0
    if foot_dict_list2:
        for item in foot_dict_list2:
            if not FindFootDict(item['foot_title'], foot_dict_list):
                items_merged += 1
                foot_dict_list.append(item)
    
    return items_merged

G_our_print_version_file = ''

def FindSectHref(opts, url_hfile, sect_label_href_list):
    """
    @summary: use url_hfile to lookup sections by either html file name or http: url
    
    @return section dictionary
    """
    global G_our_print_version_file

    for item in sect_label_href_list:
        if url_hfile[0] == '/':
            if item['html_file'] == url_hfile:
                return item
        else:
            if item['url'] == url_hfile:
                return item

    if not G_our_print_version_file:
        G_our_print_version_file = uGet1HtmlFile(opts, opts['bodir'], False)
        # This fails sometimes, don't know why... needs fixing XXX

    if not G_our_print_version_file:
        return None

    url_dname = opts['base_url']
    if os.path.basename(opts['base_url']).lower() == 'print_version':
        url_dname = os.path.dirname(opts['base_url'])

#    print url_dname, "vs", url_hfile

    # treat the current book as a special case, which we can always find... 
    if (url_hfile == G_our_print_version_file or 
        url_hfile == opts['base_url'] or
        url_hfile == url_dname):
        # pointing to ourselves:
        sect_dict = {'html_file': G_our_print_version_file,
                     'url': opts['base_url'],
                     'foot_title': opts['booknm'], 'base_id': 'Contents_root'}
        return sect_dict
    

    return None



def LabelDelWhite(label_in):
    """
    @summary: Converts all whitespace between words into a single space.

    @return:

    @note: Good for reducing text that might include carriage returns to a single line.
    """
    label_in = label_in.strip()

    label_out = ''
    prev = 'x'
    for i in range(0, len(label_in)):

        if not label_in[i].isspace():
            label_out += label_in[i]
        elif label_in[i].isspace() and not prev.isspace():
            label_out += ' '
        else:
            None
            
    return label_out

def LabelAnchSuff(label_in):

    ret_suff = LabelDelWhite(label_in)[:20]
    #if '/' in ret_suff:
    ret_suff = '_'.join(ret_suff.split('/'))
    ret_suff = ret_suff.replace(' ', '_').strip()   
    ret_suff = uCleanChars(opts, urllib.quote(ret_suff))

    return ret_suff

def AddReduceSimilarAnchors(opts, bl, url):
    """
    @summary: Find all references to URL and make them local, preserving anchors
    
    """
    
    #
    # often we don't import files with remote anchors because we think
    # that we have this information stored locally anyway. The remote file
    # is "too similar" to our current text. 
    # 
    # See if the anchor is mentioned in this doc, and reduce where possible.    
    #
    # if we can't find a local anchor, then there is no target at all and
    # we must erase the anchor text

    for tag_href in bl.find_all('a', href = True):

        if url not in tag_href['href']:
            continue

        if '#' in tag_href['href']:
            lanch = tag_href['href'].split('#')[1]

        else:
         
            lanch = os.path.basename(tag_href['href'])
             
        tag = bl.find(lambda x: x and x.has_attr('id') and 
                      x['id'] == lanch)

        # A sloppier search ignoring capitalization, I'm not sure
        # that this is worth doing, seems to be a rare circumstance
        if not tag:
            tag = bl.find(lambda x: x and x.has_attr('id') and 
                          x['id'].lower() == lanch.lower())
        
        if tag:
            tag_href['href'] = '#' + lanch
            continue

        uPlogExtra(opts, 'Can not find reference to "%s", dropping.' % ('#' + lanch), 2)

        tag_href.name = 'i'
        del tag_href['href']


def AddReduceHtmlRefs2Anchors(opts, bl, final_section_list):
    """
    @summary: Find all references to html files and convert them to anchors
    
    @note: There are a few ways we can miss these during previous processing.
    
    We might find
    
    <partial_file>.html
    <full_path>
    
    <partial_file>.html#anch
    <full_path>#anch
    
    http:<weburl>
    https:<weburl>
    http:<weburl>#anch
    https:<weburl>#anch
    
    """ 
    for how in ['exact', 'partial']:
        for section in final_section_list:
            for tag_href in bl.find_all('a', href = True):
                
                href = tag_href['href']
            
                if W2EBID in href or W2EBRI in href: 
                    # already fixed with our baseid, continue
                    continue
                
                sect_dict = FindSectHref(opts, href, final_section_list)
                if sect_dict:
                    href = sect_dict['base_id']
                    continue
                
                url = ''
                rfile = ''
                href = tag_href['href']
            
                if href[0:5] == 'http:' or href[0:6] == 'https:':
                    url = tag_href['href'].split('#')[0]
                else:
                    rfile = tag_href['href'].split('#')[0]
            
                anch = ''
                if '#' in href:
                    anch = '_Hash_' + tag_href['href'].split('#')[1]
            
                # First two are clear cut matches.
                new_id = ''
                why = ''
                if how == 'exact':
                    if url and url == section['url']: # we can reduce this one easily
                        new_id = section['base_id'] + anch
                        why = how + ' url match'
                    elif rfile and rfile == section['html_file']: 
                        new_id = section['base_id'] + anch
                        why = how + ' file match'
                else:
                    if url and (url in section['url']
                                or section['url'] in url): # we can reduce this one easily
                        new_id = section['base_id'] + anch
                        why = how + ' url match'
                    elif rfile and (rfile in section['html_file']
                                    or section['html_file'] in rfile): 
                        new_id = section['base_id'] + anch
                        why = how + ' file match'
            
                if not new_id:
                    continue
                
                uPlogExtra(opts, "Using %s to reduce %s to\n...#%s" %
                          (why, tag_href['href'], new_id), 1)
            
                tag_href['href'] = '#' + new_id
        

def AddReduceHtmlRefs2AnchorsFinal(opts, bl):
    """
    @summary: Find all references to html files and convert them to anchors or remove them
    
    @note: There are a few ways we can miss these during previous processing.
    
    We might find
    
    <partial_file>.html
    <full_path>
    
    <partial_file>.html#anch
    <full_path>#anch
    
    http:<weburl>
    https:<weburl>
    http:<weburl>#anch
    https:<weburl>#anch
    
    """ 
        
    for tag_href in bl.find_all('a', href = True):
        href = tag_href['href']

        if W2EBID in href or W2EBRI in href: 
            # already fixed with our baseid, continue
            continue
        
        if href[0:5] == 'http:' or href[0:6] == 'https:':
            # We have already tested whther these match a section URL,
            # at this stage we are done with urls
            continue

        anch = ''
        new_id =''

        if '#' in href:
            anch = tag_href['href'].split('#')[1]

            if bl.find(lambda x: x.has_attr('id') and x['id'] == anch):
                # our reference matches an anchor, nothing to do here.
                uPlogExtra(opts, "Validated href #%s" % anch, 3)
                new_id = anch # no change
            else:
                # Sledgehammerish, and potentially wrong:
                # Almost any match will do
                for tag in bl.find_all(lambda x: x.has_attr('id')):
                    if anch in tag['id']:
                        new_id = tag['id']
                        break
    
                if new_id:
                    uPlog(opts, "Reducing %s to\n...#%s" %
                         (tag_href['href'], new_id))
        
                    tag_href['href'] = '#' + new_id

        if not new_id:
            # without an anchor or a file match, we need to drop this reference.
            # we don't understand what it was pointing to. 

            del tag_href['href']
            tag_href.name = 'i'

            uPlogExtra(opts, "Missing referenat. Dropping %s" % href, 2)




def strip_square_white(opts, par_text):
    
    
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

def trim_to_footnote(bl, opts):
     
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
            ustr = strip_square_white(opts, ustr)
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

    summ0 = ShortFoot(summ[0])

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


def save_file(opts, ipath, out_data):

    ofile = open(ipath, "w+")
    
    olist = out_data
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
    ignores all symbols, punctuation and upper and lower case.
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
        sktxt = MainSketchHeading(get_text_safe(tag))
        if sktxt:
            sketch = sketch.union({sktxt})

    for tag in bl.find_all('p'):
        sktxt = MainSketchParagraph(get_text_safe(tag))
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
    
    

def PrintArticleStats(opts, im_tot, convert, sect_label_href_list, foot_dict_list,
                      slink, http404, ilink, blink):

    uPlog(opts, "\nFound", str(im_tot), "Figures,", "Converted", str(convert), "Figures")

    sfnotes = "Extracted %d Footnotes." % len(foot_dict_list)
    
    if sect_label_href_list:
        sfnotes += " Identified %d Subsections via %s heuristic." %\
        (len(sect_label_href_list), opts['stype'])
    uPlog(opts, sfnotes)

    links = 'Internet Refs = ' + str(ilink) + ', Page Refs = ' + str(blink)
    if slink:
        links += ', Bad Links Removed = ' + str(slink)
    if http404:
        links += ', http 404 = ' + str(int(http404))

    uPlog(opts, links)
        
    net_access = "Internet Accesses = " + str(opts['wgets']) + \
                         ', Cache hits = ' + str(opts['chits'])

    if opts['parent'] == '' and opts['wikidown'] > 1:
        net_access += ", %d Internet Accesss Skipped (-w)." % (int(opts['wikidown']) - 1)

    uPlog(opts, net_access)


def PrintFinalStats (opts, bl, im_tot, convert, sect_label_href_list, foot_dict_list,
                     slink, http404, toc_links, old_toc, st_time, ipath): 

    ilink = 0
    blink = 0
    
    for tag_href in bl.find_all(lambda x: Foot1HrefAll(x)):
        if tag_href['href'][0:4] == 'http':            
            ilink += 1
        else:
            blink += 1

    PrintArticleStats(opts, im_tot, convert, sect_label_href_list, foot_dict_list, slink,
                          http404, ilink, blink)
    if opts['parent'] == '':
        ostr = 'Table of Contents Entries = ' + str(toc_links)
        if old_toc > 1:
            ostr += ', Removed %d old TOC Tables' % old_toc
        uPlog(opts, ostr)
    
    uPlog(opts, "\nFinished at " + time.asctime(time.localtime(time.time())))
    uPlog(opts, "Conversion took",str_smh(time.time() - st_time))
    uPlog(opts, '')
    uPlog(opts, "wrote " + ipath)
    uPlog(opts, "==> Done")
    uPlog(opts, '')


def MainAddSections(opts, bl, sect_label_href_list):
    
    if not sect_label_href_list:
        return
    
    head = bl.find('div', class_='mw-content-ltr')
    
    assert head, 'Unable to find root of html text, mw-parser-output'
    
    head = list(head.contents)[0]
    #         
    subsections = bl.new_tag('div')
    subsections['class'] ='subsections_' + opts['footsect_name']
    head.append(subsections)

    # the parent sketch is extended each time we add a subsection.
    # lets make sure that we are not duplicating text, so recompute
    # the sketches at each stage.

    final_section_list = []

    for section in sect_label_href_list:
        
        sfile = section['html_file']
        
        assert os.path.exists(sfile), 'Unable to find section "' + section['foot_title'] + \
            '" in file: ' + str(section)
            
        with open(sfile) as fp:
            sl = BeautifulSoup(fp, "html.parser")

        uPlogExtra(opts, "==> Processing Section: " + section['foot_title'], 1)
        main_sketch = MainSketchPage(bl)
        sect_sketch = MainSketchPage(sl)
        similar = MainParentSketchVsMySketch(main_sketch, sect_sketch)
        if similar:
            uPlogExtra(opts, "...Section is too similar to existing text %s, excluding." %
                      similar, 1)
        else:
            final_section_list.append(section)


            # if there are any h1 headings demote all headings by 1
            
            if sl.find('h1'):
                for lvl in [3,2,1]:
                    for heading in sl.find_all('h' + str(lvl)):
                        heading.name = 'h' + str(lvl + 1)
                        
            # Make our new chapter heading

            uPlog(opts, '...Including Section: "'+ section['foot_title'].title() + '"')

            heading = bl.new_tag('h1')
            heading.string = section['foot_title'].title()
            heading['id'] = section['base_id']
            heading['class'] = 'chapter'

            # if we add an 'id' here then this won't be added to the TOC... 
            # need to sort this idea out, who owns the ids for headings. Do
            # we respect existing ids, or do we create new ones.
#           heading['id'] = section['id']
            
            subsections.append(heading)
            
            subsections.append(sl)
            
    AddReduceHtmlRefs2Anchors(opts, bl, final_section_list)

    AddReduceHtmlRefs2AnchorsFinal(opts, bl)
    
    return final_section_list

def MainSummaries(opts, bl, foot_dict_list):
    

    if not foot_dict_list:
        return

    #head = bl.find('div', class_='mw-parser-output')
    head = bl.find('div', class_='mw-content-ltr')
    
    assert head, 'Unable to find root of html text, mw-parser-output'
    
    head = list(head.contents)[0]
    #         
    foot_note_section = bl.new_tag('div')
    foot_note_section['class'] ='footnotes_' + opts['footsect_name']
    head.append(foot_note_section)

    # we add other details to this section, so keep the heading
    foot_head = bl.new_tag('h1', id='wiki2epub_' + opts['footsect_name'] + '_footnotes')
    foot_head.string='Footnotes'
    foot_head['class'] = 'section'
    
    foot_note_section.append(foot_head)
    
    # Do not sort foot_dict_list. Sections should appear in the same order
    # that they are found in the original text
    
    foot_dict_list.sort(key = lambda x: x['foot_title'])
    
    for item in foot_dict_list:
        # if we number our backlinks then they too are footnotes... ug. 
        num = '[' + item['ret_anch'].split('_')[2] +']'
        ftext = item['short_foot'].replace('<p><a','<p>' + num + '<a')
        
        short_foot = BeautifulSoup(ftext, 'html.parser')
        foot_note_section.append(short_foot)

    top_note = bl.new_tag('h2', id='wiki2epub_' + opts['footsect_name'] + '_notes')
    top_note.string='Notes'
    top_note['class'] = 'section'
    foot_note_section.append(top_note)
    
    for item in foot_dict_list:
        
        foot_long =''
        for par in item['long_foot']:
#            foot_long = clean_char_app(foot_long, par)
#            foot_long = uCleanChars(opts, foot_long) + uCleanChars(opts, par)
            foot_long = foot_long + par

        note = BeautifulSoup(foot_long, 'html.parser')
        foot_note_section.append(note)

def MainAddDebugHeadings(opts, bl):

    """
    @summary: Add debug headings prior to entries here so they appear in TOC
    """
    
    if opts['debug'] == 0:
        return

    head = bl.find('div', class_='mw-content-ltr')
    assert head, 'Unable to find root of html text, mw-parser-output'
    head = list(head.contents)[0]
    #         
    dbg_section = bl.new_tag('div')
    dbg_section['class'] ='debug_' + opts['footsect_name']
    head.append(dbg_section)

    dbg_head = bl.new_tag('h1', id='wiki2epub_' + opts['footsect_name'] + '_debug')
    dbg_head.string='Debug Logs'
    dbg_head['class'] = 'section'

    dbg_section.append(dbg_head)

    dbg_end = bl.new_tag('h1', id='wiki2epub_' + opts['footsect_name'] + '_debug_end')
    dbg_end.string='End'
    dbg_end['class'] = 'section'

    head.append(dbg_end) 

def MainAddDebugEntries(opts, bl):
    """
    @summary: The dubug log is kept in a file named wiki_log, include it in the ebook
    """

    if opts['debug'] == 0:
        return

    dbg_section = bl.find('div', class_='debug_' + opts['footsect_name'])

    assert dbg_section, "Could not find debug section"

    logfile = opts['bodir'] + '/wiki_log.txt'
    if os.path.exists(logfile):
        
        dbg_data1 = bl.new_tag('p')
        dbg_data1.string = "wiki2epub generates detailed logs. See: " + logfile
        dbg_section.append(dbg_data1)
    
        dbg_data2 = bl.new_tag('pre')
    
        fp = open(logfile)
        
        all_log = fp.readlines()
        fp.close()
        dbg_data2.string = ''
        for line in all_log:
            try:
                dbg_data2.string += line
            except:
                dbg_data2.string += uCleanChars(opts, line)
        
        dbg_section.append(dbg_data2)

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
    
    err, foot_dict = trim_to_footnote(bl, opts)
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

    im_tot, convert = PicGetImages(opts, bl) # easy...
    fix_easy_tags(opts, bl, section_bname)
    [sect_label_href_list, foot_dict_list, slink, http404] = FootNotes(opts, bl)

    if opts['parent']:
        uPlog(opts, '=============================================')
    else:
        uPlog(opts, '=================Finalizing==================')
        
    toc_links = 0
    old_toc = 0

    if opts['parent'] == '':
        final_sect_label_href_list = MainAddSections(opts, bl, sect_label_href_list)
        MainSummaries(opts, bl, foot_dict_list)
        while TocRemoveOldToc(opts, bl) == '':
            old_toc += 1
        MainAddDebugHeadings(opts, bl)
        toc_links = TocMake(opts, bl)
        sect_label_href_list = final_sect_label_href_list

    PrintFinalStats(opts, bl, im_tot, convert, sect_label_href_list,
                    foot_dict_list, slink, http404, toc_links, old_toc,
                    st_time, opts['footsect_name'] + '/' + section_bname)
    
    if opts['parent'] == '':
        MainAddDebugEntries(opts, bl)
    save_file(opts, opts['bodir'] + '/' + section_bname,
              bl.prettify(formatter="html").splitlines(True))
    
    return foot_dict_list, sect_label_href_list

def main(opts):
    
    st_time = time.time()
    foot_dict_list = []
    foot_dict = {}
    sect_label_href_list = []
    
    opts['footsect_name'] = uCleanChars(opts, opts['footsect_name'])
    opts['bodir'] = uCleanChars(opts, opts['bodir'])
        
    
    if not opts['footnote']:
        clean(opts)
    else:
        uSysMkdir(opts, opts['dcdir'])

    if opts['parent'] == '':
        opts['base_url'] = opts['url']
        opts['base_bodir'] = opts['bodir']

    err, bl, section_bname = get_html(opts)
    
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
                "main: no foot_dict for footnote, but no error"
        foot_dict_list = [foot_dict]

    else:
        # When a section is complete therew will be a new directory on the disk
        foot_dict_list, sect_label_href_list = MainSectionCreate(opts, st_time, bl, section_bname)

    return err, foot_dict_list, sect_label_href_list
#
# Call our main function
#

if __name__ == '__main__':
    opts = GetOptions()
    uSysCmd(opts, 'rm -r "' + opts['bodir'] + '/wiki_log.txt"', False)
    opts['parent'] = ''
    opts['parent_fp'] = ''
    opts['parent_fpc'] = 0
    opts['parent_sketch'] = ''
    opts['ret_anch'] = ''
    opts['footi'] = 1
    err, foot_dict_list, sect_label_href_list = main(opts)
    if err:
        sys.exit(1)

