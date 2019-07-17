"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""


import getopt
import sys

from bs4 import Comment
from bs4 import NavigableString

from w2ebUtils import *


def Startup():
    """
    @summary: Called for command line startup, sets the opts dict from the CLI.
    
    @note: 
    Several fields in the opts structure are only used by recursive calls and
    are not specified by the command line interface. In particular the initiating
    call must leave the 'parent' field empty, all others must define it.
    """

    opts = StartupGetOptions()
    uSysCmd(opts, 'rm -r "' + opts['bodir'] + '/wiki_log.txt"', False)
    opts['parent'] = ''         # name of the parent, empty in the CLI case
    opts['parent_fp'] = ''      # unused, development, XXX consider removing
    opts['parent_fpc'] = 0      # unused, development, XXX consider removing
    opts['parent_sketch'] = ''  # a description of the parent. See Sketch fns.
    opts['ret_anch'] = ''       # the return anchor for this footnote
    opts['footi'] = 1           # the footnote counter
    
    return opts


def StartupUsage(err):
    """
    @summary: Print the usage message. This is our basic documentation.
    """
    

    print """
W2EB - A tool for converting Wikipedia articles into ebooks."""

    if not err:
        print """
    Usage:  w2eb.py  [opts] [-u <URL>] [-b <book>] 
        
        -c        Erase .html files and retry URLs that previously failed.
        -C        Erase generated files: .html, images, and footnotes.
        -K        Erase all generated files and all cached downloads.
                    Without c, C, or K, a run will rewrite root doc only.
        -E        Export book to epub. Uses calibre for conversion.
        
        -n        No images 
        -B        Convert color images to black and white.
        -P        Convert all .svg images to .png. Older e-readers may
                    not support .svg. Wikipedia provides math equations
                    in .svg format, although converting them is time
                    consuming.
        -s        Use .svg for non-math figures. Svg figures with
                    transparent zones don't render correctly on the kindle.
                    Default is to render them.

        -u <url>  Url to use as the base of the ebook. If -b is not supplied
                    the basename of the url will be used to generate the
                    bookname, usually these match.
        -b <nm>   The name of the e-book. Wikipedia urls are usually short
                    and use the url basename as a version of the article name.
                    If -u is not supplied, guess a url based on the bookname.
              
        -d <#>    depth, 0 for no subarticles. Default is 1. 
        -S <typ>  Section type. Determines whether a link is treated
                    as a subsection or not.
                    
                    <typ> can be one of:
                    bookurl  - subsection url has book url as a substring
                    bookname - subsection url has book name as a substring
                               < default>
                    bookword - subsection url has at least one 4 letter word
                            from book name as substring
        
        -D <#>    Debug level. 0 = none, 1 = footnote only, 2 = failure only,
                    3 = all. Debug notes are included in the book by default.
        -w        Wiki down, rely on cache instead of wget (debugging...)
        -h        This message.
"""

    if err:
        print '\n' + err
        print '\nUse "-h" for help'

    print ''
    
    sys.exit(1)
        
    assert 0, "Failed to exit"



def StartupParseCLI(op):
    """
    @summary: Establish defaults for CLI options, parse op list.
    
    @return: A collection of booleans, strings, and integers.
    """
    
    
    clean_html = False
    clean_book = False
    clean_cache = False
    wikidown = 0
    export = False
    url = ""
    booknm = ''
    argc = 1
    depth = 1
    no_images = False
    wspider = 0
    bw_images = False
    svg2png = False
    svgfigs = False
    debug = 1
    stype = 'bookname'
    
    for o, a in op:
        argc += 1
        if o == '-b':
            booknm = a
        elif o == '-B':
            bw_images = True
        elif o == '-c':
            clean_html = True
        elif o == '-C':
            clean_html = True
            clean_book = True
        elif o == '-d':
            try:
                depth = int(a)
            except:
                StartupUsage('-d requires a numeric argument')
        elif o == '-D':
            try:
                debug = int(a)
            except:
                StartupUsage('-D requires a numeric argument')
        elif o == '-E':
            export = True
        elif o == '-h':
            StartupUsage('')
        elif o == '-H':
            StartupUsage('')
        elif o == '-K':
            clean_html = True
            clean_book = True
            clean_cache = True
        elif o == '-n':
            no_images = True
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
                StartupUsage('Unrecognized option for -S = %s. Use -h to get a list of valid options' % a)
        elif o == '-w':
            wikidown = 1
        elif o == '-u':
            url = a
        else:
            StartupUsage('Option "%s" not supported for arg "%s"' % (o, a))
    
    return svg2png, svgfigs, booknm, url, wikidown, clean_cache, debug, wspider,\
        stype, clean_html, clean_book, depth, no_images, bw_images, export

def StartupGetOptions():
    """
    @summary: Get command line options from the user
    
    @return: The global structure opts. 
    
    @note: opts is passed by name as the first argument to many functions,
    which allows reference to global state of page generation. opts includes
    important variables like the output directory name, and the source url name.
    """
    
    try:
        op, args = getopt.getopt(sys.argv[1:], 'Eu:b:cCKd:D:nwbphPsS:')
    except:
        StartupUsage("Error: unrecognized command line options: " +
              " ".join(sys.argv[1:]));

    if len(args) > 0:
        StartupUsage('Trailing Options Not Processed:\n' + str(args))

    svg2png, svgfigs, booknm, url, wikidown, clean_cache, debug, wspider, \
        stype, clean_html, clean_book, depth, no_images, bw_images, export = \
                                            StartupParseCLI(op)

    if svg2png and svgfigs:
        StartupUsage('Cannot combine -P and -s')

    if not booknm and url:
        booknm = uSubstrBt(url,'title=','/')
        if not booknm:
            booknm = uSubstrBt(url,'/wiki/','/Print_version')
        if not booknm:
            booknm = uSubstrBt(url,'/wiki/','/Print_Version')
        if not booknm:
            booknm = uSubstrBt(url,'/wiki/','/print_Version')
    
    if not booknm:
        StartupUsage('Need a book name. Either use an explicit "-b" or pick a different url.')

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
        # StartupUsage("Using -w requires -u")

    if wikidown and clean_cache:
        StartupUsage("Using -w relies on having cache data. Do not combine with -K")

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
            StartupUsage('Unable to guess url from book name. Maybe there is no "Print_Version"\nUse -u instead.')
                
    if url == "":
        StartupUsage("Use -u to define <URL>, or -b to define <Book>")  
    
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


TAG_FMSG = 'Fixing Tags:'

def StartupReduceProgress(opts, ma):
    """
    @summary: progress indicator for tag reduction.
    """

    if opts['clen'] > 68:
        uPlogNr(opts,'\n' + ' ' * len(TAG_FMSG))
        opts['clen'] = len(TAG_FMSG) + 1

    uPlogNr(opts, ma)
    sys.stdout.flush()

    opts['clen'] += len(ma) + 1


def StartupReduceMessyTags(opts, bl):
    """
    @summary: Remove complex HTML that can't be rendered on a Kindle
    
    @note: 
    Wikipedia pages include a lot of details that can't be easily rendered
    on a Kindle. Many of the tags are simple and always present. This fn
    gets rid of them while reporting progress.
    """
    
    # remove a lot of the noisy / non-functional elements.
    StartupReduceProgress(opts, 'sc')
#   for tag_scr in bl.html.head.find_all('script'):
    for tag_scr in bl.find_all('script'):
        tag_scr.decompose()
    
    StartupReduceProgress(opts, 'li')
    for tag in bl.html.head.find_all('link', href=True):
        tag.decompose()
    
    StartupReduceProgress(opts, 'me')
    for tag in bl.html.head.find_all('meta'):
        tag.decompose()
    
    StartupReduceProgress(opts, 'sp')
    for edit in bl.find_all('span', class_="mw-editsection"):
        edit.decompose()
    
    StartupReduceProgress(opts, 'in')
    for edit in bl.find_all('div', class_="mw-indicator"):
        edit.decompose()

    # if the only item for a tag is string based contents
    # then access it via '.string'
    StartupReduceProgress(opts, 'ti')
    bl.head.title.string = bl.head.title.string.replace(
        '/Print version - Wikibooks, open books for an open world', '')
    # these look really ugly
    StartupReduceProgress(opts, 'jl')
    for item in bl.find_all('a', class_="mw-jump-link"):
        item.decompose()

    StartupReduceProgress(opts, 'jn')
    for item in bl.find_all('div', id="jump-to-nav"):
        item.decompose()
    # these look really ugly, no print suggests they are only for the web
    StartupReduceProgress(opts, 'np')
    for item in bl.find_all('div', class_="noprint"):
        item.decompose()
    
    StartupReduceProgress(opts, 'na')
    # these look really ugly, no print suggests they are only for the web
    for item in bl.find_all('div', id='mw-navigation'):
        item.decompose()
    
    # some of this material just looks bad in an .epub
    StartupReduceProgress(opts, 'ta')
    for tag in bl.find_all('table'):
        if tag.find('a href="https://en.wikibooks.org/wiki/File:Printer.svg"'):
            tag.decompose()
    
    StartupReduceProgress(opts, 'di')
    for tag in bl.find_all('div', id='contentSub'):
        tag.decompose()
    
    StartupReduceProgress(opts, 'td')
    for tag in bl.find_all('td', class_='mbox-text'):
        tag.decompose()
    
    # ugly things near the end of the doc
    StartupReduceProgress(opts, 'ft')
    for tag in bl.find_all('div', id='footer'):
        if isinstance(tag, NavigableString):
            continue
        tag.decompose()
    
    StartupReduceProgress(opts, 'pf')
    for tag in bl.find_all('div', class_='printfooter'):
        if isinstance(tag, NavigableString):
            continue
        tag.decompose()
    
    StartupReduceProgress(opts, 'cl')
    for tag in bl.find_all('div', class_='catlinks'):
        if isinstance(tag, NavigableString):
            continue
        tag.decompose()
    
    StartupReduceProgress(opts, 'hi')
    for tag in bl.find_all('div', id='mw-hidden-catlinks'):
        if isinstance(tag, NavigableString):
            continue
        tag.decompose()
    
def StartupReduceTable(opts, bl):
    """
    @summary: Rerender Wikipedia's summary table, keeping images.
    
    @note: This function should try to preserve other elements from 
    the opening table. TODO.
    """
    
    StartupReduceProgress(opts, 'ta')
    
    for tag in bl.find_all('table', class_='infobox biota'):

        ph_tag = bl.new_tag('div')
        ph_tag['id'] = 'location of infobox biota'
        tag.insert_before(ph_tag)
        
        tag.extract()
        
        for itag in tag.find_all('img'):
            ph_tag.append(itag)
             
        

def StartupReduceTags(opts, bl, ipath):
    """
    @summary: Remove as many tags as possible

    @note: 
    wikipedia recommends downloading portions of its database
    rather than scraping .html files. This function is effectively
    simplifying the pages so they are managable, and that might
    have been avoided by just downloading text directly as suggested.
    
    Perhaps another version will do as suggested... 
    """

    # make all links to this book relative
    bname = opts['section_bname']
    footsect_name = opts['footsect_name']
    ref = 'https://en.wikibooks.org/wiki/' + footsect_name + '/'

    allanch={}
    
    fname = ref + bname
    opts['clen'] = 0

    uPlogNr(opts, '\n')
    StartupReduceProgress(opts, TAG_FMSG)

    # /for tag in bl.findall()
    i = 0;
    for anch in bl.find_all('a', href = True):
                
        anch['href'] = anch['href'].replace(fname,'')
                
        if anch['href'][0:len(ref)] == ref:
            lanch = anch['href'][len(ref):]
            
            if not lanch in allanch:
                i += 1
                if i % 2 == 0:
                    StartupReduceProgress(opts,lanch[0:2])
                
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

    StartupReduceProgress(opts,'id')

    for tag in bl.find_all('span', class_="mw-headline"):
        if tag.has_attr('id'):
            tag.parent['id'] = tag['id']
            del tag['id']
            tag.parent.contents.extend(tag.contents)
            tag.extract() # we cant decompose since we still refer to data in tag

    
    StartupReduceMessyTags(opts, bl)
    
    StartupReduceTable(opts, bl)
    
    # have found some messy stuff at the end of documents that starts with
    # a tag of the class hiddenStructure. Blow it away

    StartupReduceProgress(opts,'hi')
    
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

    StartupReduceProgress(opts,'gn')

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
            
    StartupReduceProgress(opts,'\n')  # done... 

