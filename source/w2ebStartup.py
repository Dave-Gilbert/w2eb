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

from w2ebGenText import GenTexTag2Str

from w2ebUtils import *

def Startup(basedir):
    """
    Called for command line startup, sets the opts dict from the CLI.
    
    @param basedir: The directory that all output is stored under 
    
    @note: 
    Several fields in the opts structure are only used by recursive calls and
    are not specified by the command line interface. In particular the initiating
    call must leave the 'parent' field empty, all others must define it.
    """

    opts = StartupGetOptions(basedir)
    uSysCmd(opts, 'rm -r "' + opts['bodir'] + '/wiki_log.txt"', False)
    opts['parent'] = ''         # name of the parent, empty in the CLI case
    opts['parent_sketch'] = ''  # a description of the parent. See Sketch fns.
    opts['id_anch'] = ''        # the anchor for this footnote
    opts['footi'] = 1           # the footnote counter
    
    return opts


def StartupUsage(err):
    """
    Print the usage message. This is our basic documentation.
    """
    

    print """
W2EB - A tool for converting Wikipedia articles into ebooks."""

    if not err:
        print """
    Usage:  w2eb.py  [opts] [-u <URL>] [-b <book>] 
        
        -C <#>    Clean cache, 1> failed urls + html files, 2> generated footnotes,
                  3> generated images, 4> generated equations  
        -K        Kleen cache, all generated files and all cached downloads.
        -E        Export book to epub. Uses calibre for conversion.
        
        -i        No images 
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
        -n        Never include notes, only allow footnotes
        -N        Always allow notes to be generated alongside footnotes
        -S <typ>  Section type. Determines whether a link is treated
                    as a subsection or not.
                    
                    <typ> can be one of:
                    bookurl  - subsection url has book url as a substring
                    bookname - subsection url has book name as a substring
                               < default>
                    keyword:<key_1>,<key_2>,...<key_n> - subsection has any one
                               keys in the comma separated list as a substring
        
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
    Establish defaults for CLI options, parse op list.
    
    @param op: options from call to getopt
    
    @return: A collection of booleans, strings, and integers.
    """
    
    
    clean_cache = 0
    wikidown = 0
    export = False
    url = ""
    booknm = ''
    booknm_orig = ''
    argc = 1
    depth = 1
    no_images = False
    bw_images = False
    svg2png = False
    svgfigs = False
    debug = 1
    stype = ['bookname']
    notes = 'some'
    
    for o, a in op:
        argc += 1
        if o == '-b':
            booknm_orig = a
        elif o == '-B':
            bw_images = True
        elif o == '-C':
            try:
                clean_cache = int(a)
            except:
                StartupUsage('-C requires an integer in the range 1-3')
            if clean_cache > 3 or clean_cache < 0:
                StartupUsage('-C requires an integer in the range 1-3')
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
        elif o == '-i':
            no_images = True
        elif o == '-K':
            clean_cache = 10
        elif o == '-n':
            notes = 'never'
        elif o == '-N':
            notes = 'always'
        elif o == '-P':
            svg2png = True
        elif o == '-s':
            svgfigs = True
        elif o == '-S':
            if a == 'bookurl':
                stype = ['bookurl']
            elif a == 'bookname':
                stype = ['bookname']
            elif a[0:8] == 'keyword:':
                stype = ['keyword'] + a[8:].split(',') 
            else:
                StartupUsage('Unrecognized option for -S = %s. Use -h to get a list of valid options' % a)
        elif o == '-w':
            wikidown = 1
        elif o == '-u':
            url = a
        else:
            StartupUsage('Option "%s" not supported for arg "%s"' % (o, a))
    
    return svg2png, svgfigs, booknm_orig, url, wikidown, clean_cache, debug, \
        stype, depth, no_images, bw_images, export, notes


def StartupGuessBooknm(booknm, booknm_orig, bodir, logfile, debug):
    """
    We try to guess an url based on a bookname.
    
    @param booknm: The preferred version which has had .title() applied
    @param booknm_orig: The exact version supplied on the CLI - user is right sometimes
    @param bodir: Book output dir, were processed book output files are written
    @param logfile: output data for error log
    @param debug: current debug level
    
    @note most functions just take 'opts' as their first argument, however
    during startup the opts structure is not yet fully established.
    
    @return url and booknm
    
    """

    check = "wget  -l 0 -t 3 -T 5 -o /dev/null --spider "  

    # not sure why there are 3 kinds of 'print_versions...'
    # but it seems to always be one of these
    wspider = 0
    
    lf= {'logfile': logfile, 'debug': debug}
    for booknm_guess in [booknm, booknm_orig]:
        
        urlp = "https://en.wikibooks.org/wiki/" + booknm_guess
        urlw = "https://en.wikipedia.org/wiki/" + booknm_guess

        for url in [urlp + "/Print_Version", urlp + "/Print_version",
                    urlp + "/print_version", urlp, urlw]:
        
                if os.path.exists(bodir):
                    uPlogExtra(lf, "Guessing url: " + url, 3)
                err = os.system(check + url)
                wspider += 1
                
                if not err:
                    if os.path.exists(bodir):
                        uPlogExtra(lf, "Resolved url", 3)
                    return url, booknm_guess, wspider
                    
    StartupUsage('Unable to guess url from book name. Maybe there is no "Print_Version"\nUse -u instead.')

    assert 0, "Shouldn't get here"

def StartupGetOptions(base_dir):
    """
    Get command line options from the user
        
    @note: opts is passed by name as the first argument to many functions,
    which allows reference to global state of page generation. opts includes
    important variables like the output directory name, and the source url name.

    @return: The global structure opts. 
    """
    
    try:
        op, args = getopt.getopt(sys.argv[1:], 'Eu:b:C:Kd:D:nNwbphPsS:')
    except:
        StartupUsage("Error: unrecognized command line options: " +
              " ".join(sys.argv[1:]));

    if len(args) > 0:
        StartupUsage('Trailing Options Not Processed:\n' + str(args))

    svg2png, svgfigs, booknm_orig, url, wikidown, clean_cache, debug, \
        stype, depth, no_images, bw_images, export, notes, = StartupParseCLI(op)

    booknm = booknm_orig.title()

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
            booknm = os.path.dirname(url)
    
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
        url, booknm, wspider = StartupGuessBooknm(booknm, booknm_orig, bodir, logfile, debug)
    else:
        wspider = 0

    if url == "":
        StartupUsage("Use -u to define <URL>, or -b to define <Book>")  
    
    opts = {'url':url,                  # url to download book from
            'footsect_name': booknm,    # footnote or section name, initially the same as booknm
            'booknm': booknm,           # book name, may include '/' for sub-articles
            'stype': stype,
            'clean_cache': clean_cache, # level at which to clean the cache
            'depth': depth,             # 0 = no sub articles, 1 = footnote sub article
            'footnote': False,           # whether this is a footnote, never set from CLI
            'notes': notes,
            'bodir': bodir,             # book output directory
            'dcdir': dcdir,             # download cache directory
            'no_images': no_images,     # suppress images
            'bw_images': bw_images,     # black and white images
            'svg2png': svg2png,         # convert all .svg files to .png files
            'svgfigs': svgfigs,         # use .svg for figures rather than .png
            'logfile': logfile,
            'chits': 0,                 # number of cache hits
            'stats_r': 0,               # reused footnotes from original article
            'wgets': wspider,           # number of times we fetched from the web
            'export': export,
            'debug': debug,
            'wikidown': wikidown}        # Don't use wget to access wikipedia, - slow or down
    
    # start with a fresh log file only if this is a manual invokatio
    
    return opts


TAG_FMSG = 'Fixing Tags:'

def StartupReduceProgress(opts, ma):
    """
    progress indicator for tag reduction.
    
    @param opts: dictionary of shared CLI parameters. See StartupGetOptions()
    @param ma: two character string printed to screen to indicate progress 
    
    @param opts
    """

    if opts['clen'] > 68:
        uPlogNr(opts,'\n' + ' ' * len(TAG_FMSG))
        opts['clen'] = len(TAG_FMSG) + 1

    uPlogNr(opts, ma)
    sys.stdout.flush()

    opts['clen'] += len(ma) + 1


def StartupReduceMessyTags(opts, bl):
    """
    Remove complex HTML that can't be rendered on a Kindle
    
    @param opts: dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
    
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
        #if isinstance(tag, NavigableString):
        #    continue
        tag.decompose()
    
    StartupReduceProgress(opts, 'pf')
    for tag in bl.find_all('div', class_='printfooter'):
        #if isinstance(tag, NavigableString):
        #    continue
        tag.decompose()
    
    StartupReduceProgress(opts, 'cl')
    for tag in bl.find_all('div', class_='catlinks'):
#        if isinstance(tag, NavigableString):
#            continue
        tag.decompose()

    StartupReduceProgress(opts, 'ha')
    for tag in bl.find_all('div', role='note'):
        #if isinstance(tag, NavigableString):
        #    continue
        tag.decompose()
    
    StartupReduceProgress(opts, 'hi')
    for tag in bl.find_all('div', id='mw-hidden-catlinks'):
        #if isinstance(tag, NavigableString):
        #    continue
        tag.decompose()

    StartupReduceProgress(opts, 'ss')
    for tag in bl.find_all('table', class_='mbox-small plainlinks sistersitebox'):
        #if isinstance(tag, NavigableString):
        #    continue
        tag.decompose()


def StartupTableToList(opts, bl, info_table, new_info_list):
    """
    Convert a table to a list
    
    @param opts: dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
    @param info_table: a soup representation of a table
    @param new_info_list: the root tag of the new list representation 
    
    @note: Tables don't render very well on the Kindle, so we convert them
    to bullet point lists.
    """
    prev_tag = None

    for tr_tag in info_table.find_all(lambda x: x.name in ['tr']):
        
        part_string = ''
        sep = ''
        
        if isinstance(tr_tag, NavigableString):
            part_string = uGetTextSafe(tr_tag)

        else:        
            for hd_tag in tr_tag.find_all(lambda x: x.name in ['th', 'td']):
    
                part_string, sep = GenTexTag2Str(opts, 'yes_noi', True, hd_tag,
                                                 part_string, sep)

        if len(part_string) < 2:
            uPlogExtra(opts,"Unparsed Row in Table:" + str(hd_tag), 2)
            continue

        if hd_tag.name == 'th':
            h4_tag = bl.new_tag('b')
            new_info_list.append(h4_tag)
            h4_cont = BeautifulSoup(part_string, "html.parser")
            h4_tag.append(h4_cont)
                        
        if hd_tag.name == 'td':
            if prev_tag != 'td':
                ul_tag =  bl.new_tag('ul')
                new_info_list.append(ul_tag)
            li_tag = bl.new_tag('li')
            ul_tag.append(li_tag)
            li_cont = BeautifulSoup(part_string, "html.parser")
            li_tag.append(li_cont)
            
        prev_tag = hd_tag.name

    return


def StartupReduceTableInfobox(opts, bl):
    """
    Rerender Wikipedia's summary table, keeping images.

    @param opts: dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
    
    @note: replace the table, which appears immediately after the title,
    with the first image we find in the table. We move the rest of the table
    to after the first paragraph and we convert it into a bullet list, which
    renders a little bit more consistently on a kindle.
    
    @note: This function should try to preserve other elements from 
    the opening table. TODO.
    """
    
    StartupReduceProgress(opts, 'ti')
    # We expect that there will be only one infobox. 

    info_table = bl.find(lambda x: x.name=='table' and x.has_attr('class')
                           and 'infobox' in x['class'])

    if not info_table:
        uPlogExtra(opts, "Cannot find the infobox data.", 1)
    if info_table:
        itag = info_table.find('img')
        if itag:
            ib_tag = bl.new_tag('center')
            ib_tag['id'] = 'Orig_InfoBoxLoc'
            info_table.insert_before(ib_tag)
            itag.extract()
            ib_tag.append(itag)

        info_table.extract()

        # find the first non-special paragraph entry
        par = bl.find(lambda x: x.name == 'p' and not x.has_attr('class'))

        if par:
            new_info_list = bl.new_tag('div')
            new_info_list['id'] = 'w2eb_infobox'
            
            StartupTableToList(opts, bl, info_table, new_info_list)
            par.insert_after(new_info_list)
            info_table.decompose()

        else:
            uPlogExtra(opts, "Cannot find a place for the infobox data.", 1)
            # if we can't find a paragraph there is something very wrong
            # with the page, just drop the info box in that case

    info_table = bl.find(lambda x: x.name=='table' and x.has_attr('class')
                           and 'infobox' in x['class'])
    if info_table:
        uPlogExtra(opts, "Unexpectedly found a second infobox.", 1)
    

def StartupReduceTableAll(opts, bl):
    """
    Convert all tables to bullet lists

    @param opts: dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.

    @note: The kindle has problems rendering big tables. Simplify them.
    """

    StartupReduceProgress(opts, 'ta')
    
    for info_table in bl.find_all(lambda x: x.name=='table'):

        if isinstance(info_table, NavigableString):
            continue

        new_info_list = bl.new_tag('div')
        StartupTableToList(opts, bl, info_table, new_info_list)
        info_table.replace_with(new_info_list)
        # new_info_list.decompose()


def StartupReduceTags(opts, bl):
    """
    Remove as many tags as possible
    
    @param opts: dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.

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

    StartupReduceTableInfobox(opts, bl)

    StartupReduceTableAll(opts, bl)
                
    StartupReduceProgress(opts,'\n')  # done... 

