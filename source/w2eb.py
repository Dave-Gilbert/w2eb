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

from w2ebFootNotes import FootNotes
from w2ebUtils import *





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
        final_sect_label_href_list = FinalAddSections(opts, bl, sect_label_href_list)
        FinalSummaries(opts, bl, foot_dict_list)
        while TocRemoveOldToc(opts, bl) == '':
            old_toc += 1
        FinalAddDebugHeadings(opts, bl)
        toc_links = TocMake(opts, bl)
        sect_label_href_list = final_sect_label_href_list

    FinalPrintStats(opts, bl, im_tot, convert, sect_label_href_list,
                    foot_dict_list, slink, http404, toc_links, old_toc,
                    st_time, opts['footsect_name'] + '/' + section_bname)
    
    if opts['parent'] == '':
        FinalAddDebugEntries(opts, bl)
    MainSaveFile(opts, opts['bodir'] + '/' + section_bname,
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

