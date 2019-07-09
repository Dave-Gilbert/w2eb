
import unicodedata

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



