


def Startup():

    opts = StartupGetOptions()
    uSysCmd(opts, 'rm -r "' + opts['bodir'] + '/wiki_log.txt"', False)
    opts['parent'] = ''
    opts['parent_fp'] = ''
    opts['parent_fpc'] = 0
    opts['parent_sketch'] = ''
    opts['ret_anch'] = ''
    opts['footi'] = 1
    
    return opts


def StartupUsage(err):

    print """
wiki_get.py, A script for fetching html versions of Wikibooks."""

    if not err:
        print """
    StartupUsage:  wiki_get.py  [opts] [-u <URL>] [-b <book>] 
        
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


def StartupGetOptions():
    
    try:
        op, args = getopt.getopt(sys.argv[1:], 'Eu:b:cCKd:D:nwbphPsS:')
    except:
        StartupUsage("Error: unrecognized command line options: " +
              " ".join(sys.argv[1:]));

    if len(args) > 0:
        StartupUsage('Trailing Options Not Processed:\n' + str(args))

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
                StartupUsage('Unrecognized option for -S = %s. Use -h to get a list of valid options' % a)
            
        elif o == '-K':
            clean_html = True
            clean_book = True
            clean_cache = True
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
        elif o == '-n':
            no_images = True
        elif o == '-w':
            wikidown = 1
        elif o == '-E':
            export = True
        elif o == '-u':
            StartupUsage('')
        else:
            StartupUsage('Option "%s" not supported for arg "%s"' % (o,a))

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
    @summary: progress indicator for tag fixing. With big HTML files it can take a bit
    """

    if opts['clen'] > 68:
        uPlogNr(opts,'\n' + ' ' * len(TAG_FMSG))
        opts['clen'] = len(TAG_FMSG) + 1

    uPlogNr(opts, ma)
    sys.stdout.flush()

    opts['clen'] += len(ma) + 1

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

    
    # remove a lot of the noisy / non-functional elements.

    StartupReduceProgress(opts,'sc')
                                      
#   for tag_scr in bl.html.head.find_all('script'):
    for tag_scr in bl.find_all('script'):
        tag_scr.decompose()

    StartupReduceProgress(opts,'li')

    for tag in bl.html.head.find_all('link', href=True):
        tag.decompose()

    StartupReduceProgress(opts,'me')

    for tag in bl.html.head.find_all('meta'):
        tag.decompose()

    StartupReduceProgress(opts,'sp')
    
    for edit in bl.find_all('span', class_="mw-editsection"):
        edit.decompose()

    # if the only item for a tag is string based contents
    # then access it via '.string'        

    StartupReduceProgress(opts,'ti')

    bl.head.title.string = bl.head.title.string.replace(
        '/Print version - Wikibooks, open books for an open world','')

    # these look really ugly 
    StartupReduceProgress(opts,'jl')

    for item in bl.find_all('a', class_="mw-jump-link"):
        item.decompose()

    # these look really ugly, no print suggests they are only for the web
    StartupReduceProgress(opts,'np')

    for item in bl.find_all('div', class_="noprint"):
        item.decompose()

    StartupReduceProgress(opts,'na')

    # these look really ugly, no print suggests they are only for the web
    for item in bl.find_all('div', id='mw-navigation'):
        item.decompose()
        
    # some of this material just looks bad in an .epub

    StartupReduceProgress(opts,'ta')
    
    for tag in bl.find_all('table'):
    
        if tag.find('a href="https://en.wikibooks.org/wiki/File:Printer.svg"'):
            tag.decompose()

    StartupReduceProgress(opts,'di')

    for tag in bl.find_all('div', id='contentSub'):
        tag.decompose()

    StartupReduceProgress(opts,'td')
       
    for tag in bl.find_all('td', class_='mbox-text'):
        tag.decompose()

    # ugly things near the end of the doc

    StartupReduceProgress(opts,'ft')

    for tag in bl.find_all('div', id='footer'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()

    StartupReduceProgress(opts,'pf')

    for tag in bl.find_all('div', class_='printfooter'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()

    StartupReduceProgress(opts,'cl')

    for tag in bl.find_all('div', class_='catlinks'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()

    StartupReduceProgress(opts,'hi')

    for tag in bl.find_all('div', id='mw-hidden-catlinks'):
        if isinstance(tag, NavigableString):
                continue
        tag.decompose()
            
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

