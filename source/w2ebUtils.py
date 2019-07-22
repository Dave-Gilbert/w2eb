"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

# VERSION = 0.3

import unicodedata
import os
import urllib
import time
import string

from bs4 import BeautifulSoup

from w2ebConstants import *

def uSubstrBt(Str, pre, post):
    """
    Get the substring between two other strings
    
    @return: The substring
    """
    
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


def uGetTextSafe(curr):
    """
    Beautiful Soup objects often have text, but not always.
    
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
    Collect the html file defined by opts.  
    
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
        section_bname = urllib.unquote(uCleanChars(os.path.basename(htmlfile)))

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


def uGenRetAnch(opts, foot_dict, foot_title):
    """
    Add return anchor to foot_dict, increment footi if necessary.
    
    @note The same footnote is often referenced multiple times. We create a
    list of return anchors and add them to the foot dict. This function makes
    the new return anchor, adds it to the list.
    
    @note id_anch should be used to construct destination ids, 
    """

    if not 'id_anch' in foot_dict: 
        ret_suff = uLabelDelWhite(foot_title)[:50]
        #if '/' in ret_suff:
        ret_suff = '_'.join(ret_suff.split('/'))
        ret_suff = ret_suff.replace(' ', '_').strip()   
        ret_suff = urllib.quote(uCleanChars(ret_suff))
        
        if ret_suff:
            id_anch = W2EBRI + '%d_%s' % (opts['footi'], ret_suff)
        else:
            id_anch = W2EBRI + '%d' % opts['footi']
            

        foot_dict['id_anch'] = id_anch
        opts['footi'] += 1
        foot_dict['ret_anch_all'] = []

    # add a trailing index, as there are often duplicates

    let = string.ascii_lowercase[len(foot_dict['ret_anch_all'])]
    ret_anch = foot_dict['id_anch'] + '_' + let

    foot_dict['ret_anch_all'].append(ret_anch)


def uClean(opts):
    """
    Cleanup old files, removed cached content, create directories.
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
    
    if opts['clean_cache'] >= 3:
        assert not opts['bodir'] in cwd, cwd_msg 
        uSysCmd(opts, 'rm -r "' + opts['bodir'] + '"', False)

    uSysMkdir(opts, opts['bodir'])
    
    if opts['parent'] == '':

        if opts['clean_cache'] >= 1:
            uPlog(opts, '')
            uSysCmd(opts, 'find "' + opts['bodir'] +'" -name \*.html -exec rm \{\} \;' , False)
            uPlog(opts, "Removing generated html files, and failed urls from the cache.")

        if opts['clean_cache'] >= 2:
            uSysCmd(opts, 'rm "' + opts['bodir'] + '/footnotes/"*', False)
            uPlog(opts, "Removing all notes and footnotes from the cache, all urls to be reverified.")

        if opts['clean_cache'] >= 3:
            uPlog(opts, "Removing all generated images, and equations.")

        if opts['clean_cache'] >= 10:

            assert not opts['dcdir'] in cwd, cwd_msg
            uSysCmd(opts, "rm -r " + opts['dcdir'] , False)
            uPlog(opts, "Removing all data previously downloaded from the Internet")

    uSysMkdir(opts, opts['bodir'] + '/images')
    uSysMkdir(opts, opts['bodir'] + '/footnotes')

    uSysMkdir(opts, opts['dcdir'])
    uSysMkdir(opts, opts['dcdir'] + '/images')
    uSysMkdir(opts, opts['dcdir'] + '/footnotes')


def uBurn2Ascii(str_in):
    """
    hack: we force conversion when standard filters fail, with ugly results
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
    
    return str_out


def uCleanChars(str_in):
    """
    This function ought only be called if we are seeing unhandled exceptions
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
        None
    
    if not done: # try again with burnedascii as our input
        burnedascii = uBurn2Ascii(str_in)
        burneduni = unicode(burnedascii, 'unicode-escape')
        str_out = unicodedata.normalize('NFKD', burneduni).encode('ascii','replace')
    
    return(str_out)


def uPlogExtra(opts, o_string, dbg):
    """
    Appends a string to our regular log file, skips stdout
    """
    if dbg > opts['debug']:
        return
    
    ofp = open(opts['logfile'], "a")
    ofp.write(uCleanChars(o_string + '\n'))
    ofp.close()

def uPlogFile(opts, filename, dbg):
    """
    Include additional file in log
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
     print to stdout and log, by default add a carriage return
    """
    uPlogCr(opts, True, *msgs)

def uPlogNr(opts, *msgs):
    """
    Print to stdout only. Don't add a carriage return
    """

    uPlogCr(opts, False, *msgs)

def uPlogCr(opts, cr, *msgs):
    """
    Writes messages to both wiki_log.txt and stdout. cr toggles stdout only with continuatin
    """

    sep = ''
    o_string = ''
    for word in msgs:
        o_string = uCleanChars(o_string + sep + word)
        sep = ' '

    if opts['debug'] > 0:
        ofp = open(opts['logfile'], "a")
        if cr:
            ofp.write(uCleanChars(o_string + '\n'))
        ofp.close()

    if cr and not opts['footnote']:
        print uCleanChars(o_string)

    if not cr and not opts['footnote']:
        print uCleanChars(o_string),



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
    Get the name of the first .html file in the directory.
    
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
    Emulate mkdir -p behaviour, create all subidirs unless the exist
    
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
        syserr = 'failed: ' + uCleanChars(cmdstr) + ' ' + str(e)
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
            uPlog(opts, '\n\nfailed: ' + uCleanChars(cmdstr) + '\n\n')
            uPlog(opts, e)
            raise
        syserr = 1

        assert not (syserr and catch_errors), '\n\nfailed: ' + uCleanChars(cmdstr)
    
    return outlines

def uSysCmdOut1(opts, cmdstr, catch_errors):
    
    rval = uSysCmdOut(opts, cmdstr, catch_errors)
    
    if rval:
        return rval[0]
    return ''

def uStrTimeSMH(secs):
    
    if secs < 180:
        retval = "%3d secs" % int(secs)
    elif secs < 7200:
        retval = "%3d mins" % int((30 + secs)/60)
    else:
        retval = "%2d hours" % int(secs/3600)
    
    return retval

def uPrintProgress(opts, st_time, im_tot, im_all, p_total_est_time):
    
    perc = int(100 * im_tot / im_all)                
    t2 = time.time()
    
    if im_tot == 0:
        total_est_time = p_total_est_time
    else:
        total_est_time = ((t2 - st_time) * im_all) / im_tot
        total_est_time = (total_est_time + p_total_est_time) / 2
        
    if im_tot > 60: 
        p_total_est_time = total_est_time # smoothing factor
        
    secs = int((total_est_time - (t2 - st_time)))
    
    if secs < 1:
        secs = 1
                
    uPlogNr(opts, "\n%2s %% %s left" % (perc, uStrTimeSMH(secs)),">")
        
    return p_total_est_time


def uLabelDelWhite(label_in):
    """
    Converts all whitespace between words into a single space.

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

G_our_print_version_file = ''

def uFindSectHref(opts, url_hfile, sect_label_href_list):
    """
    use url_hfile to lookup sections by either html file name or http: url
    
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


def uUrlOk(opts, url, footsect_name):
    """
    Limit our search to wikipedia articles
    
    @param url
    @param footsect_name
    """
       
    # don't download exactly ourselves
    if url == 'https://en.wikibooks.org/wiki/' + footsect_name:
        return False
    if url in opts['url']:
        return False
    if '&action=' in url:
        return False
    if url[-6:] == '/wiki/':
        return False
    if 'wikipedia.org' in url:
        return True
    if 'wikibooks.org' in url:
        return True

    return False

def uHrefOk(tag_href, exclude_internal):
    """
    Verify that soup tag is an anchor with an href and other properties
    
    @param tag_href -- a soup tag
    @param exclude_internal -- Whether or not to allow internal references
    
    This function is used as part of a BeautifulSoup find_all() call to
    filter out tags that we will or wont try to make into footnotes.
    
    When we search for tags to modify we don't want to change anything
    that refers to the current page. We have a separate search that also
    uses this filter to count all references for statistics purposes.
    """
   
    if not tag_href.name == 'a':
        return False
    
    if not tag_href.has_attr('href'):
        return False

    url = tag_href['href']
    
    if not url:
        return False

    suff = url[-4:]
    
    # We have already resolved the images that we can
    # at this stage, we don't annotate them further
    
    if (suff in IMAGE_FIG + IMAGE_PIC + IMAGE_SVG + SUFFIX_OT):
        # don't mark up images, or other special objs
        return False

    if exclude_internal:
        if url[0:4] != 'http':
            # page link is internal, don't mark it up
            return False
    
    return True

def uHrefRemote(tag_href):
    """
    True if tag is an anchor that refers to a remote footnote or section
    """
    return uHrefOk(tag_href, True)


def uFindFootDict(foot_title, foot_dict_list):
    """
    Look up foot_title in a list of foot dictionaries.
    
    @return: None if not found, o.w. a footnote dictionary
    """

    for foot_dict in foot_dict_list:
        if foot_dict['foot_title'] == foot_title:
            return foot_dict
    
    return None

def uMergeSectUniq(opts, sect_label_href_list, sect_label_href_list2):
    """
    Merge two section lists, include unique items only
    """
    items_merged = 0
    if sect_label_href_list:
        for item in sect_label_href_list2:
            if not uFindSectHref(opts, item['html_file'], sect_label_href_list):
                items_merged += 1
                sect_label_href_list.append(item)

    return items_merged


def uMergeFootUniq(foot_dict_list, foot_dict_list2):
    """
    Merge two footnote lists, include unique items only
    """
    items_merged = 0
    if foot_dict_list2:
        for item in foot_dict_list2:
            if not uFindFootDict(item['foot_title'], foot_dict_list):
                items_merged += 1
                foot_dict_list.append(item)
    
    return items_merged

def uSaveFile(opts, ipath, olist):
    """
    Save our new html file
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



