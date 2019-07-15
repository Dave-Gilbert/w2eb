
import unicodedata

def uGetTextSafe(curr):
    """
    @summary: Beautiful Soup objects often have text, but not always.
    
    @return: Return any text found, or the empty string if there is no text.
    """
    
    
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


def uGetHtml(opts):
    """
    @summary: Collect the html file defined by opts.  
    
    @param opts
    
    Gets whatever uGetHtml will collect for a url in opts and 
    returns the basename of that file for use as a reference.
    
    Extract the htmlsoup and save the .html file in the cache
    
    @return: (err - any error that occurs,
              bl - the Beautiful Soup Structure
              section_bname - the basename of the URL)
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


def uClean(opts):
    """
    @summary: Cleanup old files, removed cached content, create directories.
    """
    
    del_msg = "XXXX What are we trying to delete? Everything? THIS IS A BAD BUG...XXXX"
    assert len(opts['bodir']) > 10, del_msg
    assert len(opts['dcdir']) > 10, del_msg

    #
    # If we are running on a subarticle don't chatter about cleaning up
    # directories, we will already have this message in the parent
    #

    cwd = os.getcwd()
    
    cwd_msg = "\n\nUnable to uClean the current working directory.\n Try cd ..\n"
    
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


def uBurn2Ascii(str_in):
    """
    @summary: hack: we force conversion when standard filters fail, with ugly results
    """

    ba = bytearray(str_in)

    str_out = ''
    bad_chrs = []

    for i in range(0, len(ba)):
#        if ba[i] < 32 or ba[i] > 126:
        if ba[i] < 32 or ba[i] > 126 or ba[i] == 92:

            str_out += '_'
            bad_chrs += [[i, ba[i]]]
        else:
            str_out += chr(ba[i])
    
    uPlogExtra(opts, "Replaced bad characters with '_'. Check " + str(bad_chrs), 1)
    uPlogExtra(opts, "XXX mangled string is now" + str_out, 1)

    return str_out


def uCleanChars(opts, str_in):
    """
    @summary:  this function ought only be called if we are seeing unhandled exceptions
            It creates as many problems as it solves, hence the noise. 
    """
    
    str_out = ''
    done = False
    
    if not isinstance(str_in, unicode):
        try:
            str_in = unicode(str_in, 'unicode-escape')
        except Exception as e:
            None
#            str_in = burntoascii(str_in)
    try:
#       str_out = unicodedata.normalize('NFKD',str_in).encode('utf8','ignore')
        str_out = unicodedata.normalize('NFKD',str_in).encode('ascii','replace')
        done = True
    except Exception as e:
        uPlogExtra(opts, 'XXX2 Caught encoding exception on string len = %d' % len(str_in), 1)
        None
    
    if not done: # try again with burnedascii as our input
        burnedascii = uBurn2Ascii(str_in)
        burneduni = unicode(burnedascii, 'unicode-escape')
        str_out = unicodedata.normalize('NFKD', burneduni).encode('ascii','replace')
    
    return(str_out)



def uPlogExtra(opts, o_string, dbg):
    """
    @summary: Appends a string to our regular log file, skips stdout
    """
    if dbg > opts['debug']:
        return
    
    ofp = open(opts['logfile'], "a")
    ofp.write(uCleanChars(opts, o_string + '\n'))
    ofp.close()

def uPlogFile(opts, filename, dbg):
    """
    @summary: Include additional file in log
    """
    if dbg > opts['debug']:
        return

    i = filename.find(opts['footsect_name'])
    file_showname = filename[i:]

    ofp = open(opts['logfile'], "a")

    if os.path.exists(filename):
        ofp.write('-----------file = ' + file_showname + '\n')

        fp = open(filename, 'r')
        file_lines = fp.readlines()

        for line in file_lines:
            # ofp.write(uCleanChars(opts, line))
            ofp.write(line)
            ofp.write('\n')
        ofp.write('--------------\n')
        ofp.close()
        fp.close()
        
        
    else:
        ofp.write('File not found:' + filename + '\n')
    ofp.close()

def uPlog(opts, *msgs):
    """
    @summary:  print to stdout and log, by default add a carriage return
    """
    uPlogCr(opts, True, *msgs)

def uPlogNr(opts, *msgs):
    """
    @summary:  print to stdout only. Don't add a carriage return
    """

    uPlogCr(opts, False, *msgs)

def uPlogCr(opts, cr, *msgs):
    """
    @summary:  Writes messages to both wiki_log.txt and stdout. cr toggles stdout only with continuatin
    """

    sep = ''
    o_string = ''
    for word in msgs:
        o_string = uCleanChars(opts, o_string + sep + word)
        sep = ' '

    if opts['debug'] > 0:
        ofp = open(opts['logfile'], "a")
        if cr:
            ofp.write(uCleanChars(opts, o_string + '\n'))
        ofp.close()

    if cr and not opts['footnote']:
        print uCleanChars(opts, o_string)

    if not cr and not opts['footnote']:
        print uCleanChars(opts, o_string),



def uGetFlistFromDir(ls_dir, prefix, ext, must_get):
    
    
    ofiles = []
    
    if must_get:
        assert os.path.isdir(ls_dir), "Expected %s to be a directory. It is not." % ls_dir
    
    try:
        ls_files = os.listdir(ls_dir)
        
        for ext_file in ls_files:
            if os.path.isdir(ls_dir + '/' + ext_file):
                continue
    
            if prefix and not ext_file[:len(prefix)] == prefix:
                continue
            
            if ext_file[-len(ext):] == ext:
                ofiles += [ls_dir + '/' + ext_file]

    except Exception:
        
        None

    return ofiles

def uGet1HtmlFile(opts, ls_dir, must_get):
    """
    @summary: Get the name of the first .html file in the directory.
    
    @param ls_dir - directory to check
    @param must_get - whether multiple entries are tollerated. They shouldn't be.
    
    @return (zero or one .html filenames)
    """
    
    ret_file = ''
    c = 0
    
    if must_get:
    
        htm_files = uGetFlistFromDir(ls_dir, None, '.html', must_get)
        c = len(htm_files)
    
        assert c == 1, "Expected exactly one .html file. Found " + \
            str(c) + "\n" + str(htm_files)
    else:
        try: 
            htm_files = uGetFlistFromDir(ls_dir, None, '.html', must_get)
            c = len(htm_files)
        except Exception as e:
            uPlogExtra(opts, 'uGet1HtmlFile exception' + e, 1) 

    if c > 0:
        ret_file = htm_files[0]
        
    return ret_file

def uSysMkdir(opts, dirname):
    """
    @summary: Emulate mkdir -p behaviour, create all subidirs unless the exist
    
    """
    
    if os.path.exists(dirname) and os.path.isdir(dirname):
        return 
    
    if os.path.exists(dirname):
        assert 1, "Found file when expecting a directory name " + dirname
    
    dir_list = dirname.split('/')
    dir_part = ''
    for dbasename in dir_list:
        dir_part += '/' + dbasename
        if not os.path.exists(dir_part):
            os.mkdir(dir_part)

# def sys_cp(opts, ...)

def uSysCmd(opts, cmdstr, catch_errors):

    code = 0
    syserr = None
    if not catch_errors:
        cmdstr = cmdstr  + ' >/dev/null 2>&1'

    try:
        code = os.system(cmdstr)
    except Exception as e:
        syserr = 'failed: ' + uCleanChars(opts, cmdstr) + ' ' + str(e)
        if catch_errors:
            uPlog(opts, '\n\n' + syserr + '\n\n')
            uPlog(opts, e)
            raise
        code = 1

    if not syserr and code:
        syserr = 'failed: %s with code = %d' % (cmdstr, code) 
    
    assert not (code and catch_errors), '\n\n' + syserr + '\n'
    if False: # very noisy, we should do fewer things in the shell
        uPlogExtra(opts, "EXEC: " + cmdstr, 1)

    return syserr

def uSysCmdOut(opts, cmdstr, catch_errors):
    # don't have a good way to capture stderr messages. popen is deprecated
    # you are suppose to use some other commands... needs research time to fix.
    # there are other ways to launch processes in python. 

    syserr = 0
    if not catch_errors:
        cmdstr = cmdstr  + ' lies 2>/dev/null'
    
    fp = open('/dev/null','a')
    assert fp
    
    try:
        fp = os.popen(cmdstr)  
        if fp:
            outlines = fp.readlines()
            outlines = [ x.strip() for x in outlines ]
            fp.close()

    except Exception as e:
        if catch_errors:
            uPlog(opts, '\n\nfailed: ' + uCleanChars(opts, cmdstr) + '\n\n')
            uPlog(opts, e)
            raise
        syserr = 1

        assert not (syserr and catch_errors), '\n\nfailed: ' + uCleanChars(opts, cmdstr)
    
    return outlines

def uSysCmdOut1(opts, cmdstr, catch_errors):
    
    rval = uSysCmdOut(opts, cmdstr, catch_errors)
    
    if rval:
        return rval[0]
    return ''

def uPrintProgress(opts, st_time, im_tot, im_all, p_total_est_time):
    
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
    
    if secs < 1:
        secs = 1
                
    uPlogNr(opts, "\n%2s %% %s left" % (perc, str_smh(secs)),">")
        
    return p_total_est_time

def uLabelDelWhite(label_in):
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

