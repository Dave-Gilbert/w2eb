"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

import urllib
import json
import traceback
import time
import sys

from bs4 import NavigableString

from w2ebUtils import *
from w2ebConstants import *

from w2ebFinal import FinalReduceSimilarAnchors 

from w2ebGenText import GenTextGetFootNote
from w2ebPic import PicGetImages
from w2ebStartup import StartupReduceTags
from w2ebSketch import SketchPage
from w2ebSketch import SketchVsMySketch
from w2ebLocalRefs import LocalReuse 
from w2ebLocalRefs import LocalRaiseAnchor 

from w2ebFinal import FinalMergeFootSectTOC


def MainRecursiveCall(opts, bl, url, ret_anch,
                err, footnote, foot_title, foot_dict_list):
    """
    Fetches footnotes and subarticles by calling main function
    
    @return (err - any errors encountered as a string,
             foot_dict - footnote data stored in a dictionary)
             
     @note:
     Subsections are returned implicitly by collecting data in bodir.
     Notice that we make a new 'bodir' for this invocation that is
     the current bodir / basename(url)
     
     For footnotes, turning on the footnote flag causes us to write
     output in the current directories "footnote" directory. We also
     return the same data in a dictionary structure from main. 
    """
        
    foot_dict = {}

    opt2_notes = opts['notes']
    if not footnote and opts['depth'] <= 1 and opts['notes'] == 'some':
            opt2_notes = 'never'

    opt2 = {'url':url,
        'base_url': opts['base_url'],       # base_url + '/' + booknm == url
        'base_bodir': opts['base_bodir'],
        'booknm': opts['booknm'],
        'stype': opts['stype'],
        'footsect_name': opts['footsect_name'],
        'clean_cache': 0, # only the root should clean the whole cache
        'depth': opts['depth'] - 1, 
        'footnote': footnote,
        'notes': opt2_notes, 
        'bodir': opts['bodir'] + '/' + os.path.basename(url), 
        'dcdir': opts['dcdir'] + '/' + os.path.basename(url), 
        'no_images': footnote or opts['no_images'],
        'bw_images': opts['bw_images'],
        'svg2png': opts['svg2png'],
        'svgfigs': opts['svgfigs'],
        'ret_anch': ret_anch, 
        'parent': opts['section_bname'],
        'parent_fpc': 0, 
        'parent_sketch': opts['my_sketch'], 
        'logfile': opts['logfile'], 
        'chits': 0,
        'wgets': 0,
        'footi': opts['footi'],
        'export': False,
        'wikidown': opts['wikidown'],
        'debug': opts['debug']}

    if footnote:
        opt2['footsect_name'] = foot_title 

    # only the top level parent allows children to write to sys.stdout
    if opts['parent']:
        opt2['parent_fp'] = None

    if opts['debug'] > 0: # we want to stop if debugging is on 
        if footnote:
            err, foot_dict = GenTextGetFootNote(opt2)
            sect_label_href_list = []
        else:
            [err, foot_dict_list2, sect_label_href_list] = Main(opt2)
    else:
        try:
            if footnote:
                err, foot_dict = GenTextGetFootNote(opt2)
            else:
                [err, foot_dict_list2, sect_label_href_list] = Main(opt2)

        except Exception as e:
            uPlog(opts, '')
            uPlog(opts, "Problem fetching", url)
    
            fp = open(opts['logfile'], 'a')
            uPlog(opts, "Caught Exception", repr(e))
            traceback.print_exc(None, fp) 
            traceback.print_exc()
            fp.close()
                
            err = 'exception ' + uCleanChars(opts, repr(e))
            err.replace(' ', '_')

    # if wikidown is nonzero our child will increment it if necessary
    if footnote:
        assert bool(err) ^ bool(foot_dict), "Expected one of err or foot_dict."

    else:
        if not err:
            items_merged = uMergeFootUniq(foot_dict_list, foot_dict_list2)
            uPlogExtra(opts, "Footnote items merged = %d." % items_merged, 2)

    opts['chits'] = opts['chits'] + opt2['chits']
    opts['wgets'] = opts['wgets'] + opt2['wgets']
    opts['wikidown'] = opt2['wikidown']
    opts['footi'] = opt2['footi']

    
    return err, foot_dict, sect_label_href_list


def MainGetCachedFootSect(opts, foot_dict_list,
                       footnote, outdir, foot_title, url, sect_label_href_list,
                       sect_label_href_list_child):
    """
    Look for foot_title data in both memory and disk cache
    
    @return (cache_hit - whether we found foot_title or not,
             foot_dict - the information for footnotes)

    """
    cache_hit = False
    foot_dict = {}
    sect_dict = {}
    
    if footnote:
        foot_dict = uFindFootDict(foot_title, foot_dict_list)
        if foot_dict:
            cache_hit = True

            if foot_dict['msg'] == 0:
                uPlogExtra(opts, 'Cache hit: ' + foot_dict['foot_title']
                               +', id="#' + foot_dict['ret_anch'] + '_foot"', 3)
                # only mention a found footnote one time.
                foot_dict['msg'] = 1

    else:
        
        sect_dict = uFindSectHref(opts, url, sect_label_href_list + sect_label_href_list_child)
        if sect_dict:
            cache_hit = True
            uPlogExtra(opts, "Found Section Url %s in cache." % url, 2)
        else:
            html_file = uGet1HtmlFile(opts, outdir, False)
            if html_file:
                cache_hit = True

                base_id = MainGenBaseId(opts, url)
                sect_dict = {'html_file': html_file, 'url': url,
                             'foot_title': foot_title, 'base_id': base_id}
            
                sect_label_href_list.append(sect_dict)

    return cache_hit, foot_dict, sect_dict


def MainGetHref(opts, foot_dict_list, anch, footnote,
                  foot_title, foot_dict, outdir, sect_dict, url):
    """
    Return the href for footnotes and sections
    
    @return: (href - the html field for href=

    @note: At this stage we have either found the reference as a footnote,
           or a full section. Whether it was in the cache or not doesn't
           matter at this stage. We should be able to complete the href.
           
           The special case for depth = 0 means that we definitely did not
           download new material. At depth = 0 we might have found a cached
           reference, but if not we return the URL as the href.
           
           If we don't have an href by the end of this fn there is a bug.
    """

    err = ''
    href = ''
    htmlfile=''
    if not footnote:

        if not sect_dict and opts['depth'] == 0:
            href = url
        else:
        
            if not anch:
                href = '#' + sect_dict['base_id']
            else:
                href = '#' + sect_dict['base_id'] + '_Hash_' + anch

    else:

        if not foot_dict and opts['depth'] == 0:
            href = url
        else:
            href = '#' + foot_dict['ret_anch']  + '_foot'

    if not err:
        assert href , "Should have found an href, or not called this fn.\n" + \
            "anch = " + str(anch) +", footnote = " + str(footnote) + "\nfoot_title = " + \
            str(foot_title) + ", url = " + str(url) + "\ndepth = " + str(opts['depth']) + \
            ", htmlfile=" + str(htmlfile) + "\nfoot_dict:\n" + str(foot_dict)   

    return err, href


def MainGenBaseId(opts, url):
    """
    Given either an url or an html file compute the base_id used to locate pages
    """
    
    
    htp = 'https:/'
    if url[:len(htp)] != htp:
        url.replace(opts['base_bodir'],opts['base_url'])  
    base_id = url[len(htp):].replace(' ','_').replace('/','_').replace('.','_')
    base_id = W2EBID + urllib.quote(base_id)

    return base_id

def MainUpdateHTMLTag(opts, bl, tag_href, ret_anch, footnote, foot_title,
                        href, cache_hit, sect_label_href_list):
    """
    Modify footnote tag_href. For Sections build up list of href details.

    We add the return anchor to our href tag for both sections and footnotes.
    
    For footnotes we create a number in parenthesis which we append to the anchor.
    """

    if footnote:

        tag_num = bl.new_tag("i")
        num = ' [' + ret_anch.split('_')[2] +']'  # XXX compute the ind from ret_anch
        tag_num.string = num

        if True: # hardwired to include number as part of the link, but switchable
            tag_href.append(tag_num) # include num as part of link
        else:
            tag_href.insert_after(tag_num)

        LocalRaiseAnchor(tag_href, ret_anch)

    else:
        # we don't do anything special for section hrefs (should we?)
        None
    
    tag_href['href'] = href


def MainFinalChecksRetPsym(opts, foot_dict_list, footnote, foot_title, cache_hit, foot_dict):

    if footnote and opts['depth'] > 0:
        assert foot_title and uFindFootDict(foot_title, foot_dict_list) , \
            'Footnote "' + foot_title + '" not in foot dictionary? Should be an error.\n' +\
            'Have %d items in footnote list.' % len(foot_dict_list)
    if foot_dict:
        assert foot_dict['foot_title'] == foot_title, "Label mismatch: " + \
            foot_dict['foot_title'] + " =/= " + foot_title
    if footnote and not cache_hit:
        uPlogExtra(opts, 'Adding Footnote: ' + foot_title, 3)
    
    if not cache_hit and opts['depth'] == 0:
        psym = 'I'
    else:
        if footnote:
            psym = 'F'
        else:
            psym = 'A'
        if cache_hit:
            psym = psym.lower()

    return psym


def MainIsFootnote(opts, tag_href, url):
    """
    Decide if href points to a footnote, or not.
    
    @return: True if its a footnote
    """
    
    footnote = True
    
    if opts['depth'] > 0:
        if (opts['stype'][0] == 'url' and opts['base_url'] in url):
            uPlogExtra(opts, "Identified SubSection based on url match.\n%s < %s\n"
                       % (opts['base_url'], url), 2)
            footnote = False
        elif (opts['stype'][0] == 'bookname' and opts['booknm'].lower() in
              url.lower()):
            uPlogExtra(opts, "Identified SubSection based on book name match.\n%s < %s\n"
                       % (opts['booknm'], url), 2)
            footnote = False
        elif (opts['stype'][0] == 'keyword'):
            for word in opts['stype'][1:]:
                if word.lower() in url.lower():
                    uPlogExtra(opts, "Identified SubSection based on a keyword match.\n%s < %s\n"
                               % (word, url), 2)
                    footnote = False
                    break
    
    return footnote


def MainPickFootVsSect(opts, tag_href):
    """
    Decide whether the tag will be processed as a section or a footnote
    
    @return: (err - any detecte errors
              url - the url with any associated '#' anch removed
              anch - empty or the urls anchor
              footnote - boolean, True if a footnote, false if a section
              foot_title - The name of the footnote or section
              ret_anch - The return anchor. Also used as the base for footnote id.
              
    @note ret_anch has multiple functions. It is the id for this tag, hence the
          "return anchor" or the location that footnote will link to bring us
          back to the text. It is also the id for the footnote with the suffix
          "_foot" appened to it. This provides us with unique bidirectional linkage.
    """

    err = ''
    anch = ''
    ret_anch = ''
    foot_dict = {}
    url = tag_href['href']


    footnote = MainIsFootnote(opts, tag_href, url)

    if '#' in url:
        anch = url.split('#')[1]
        url = url.split('#')[0]
    foot_title = uLabelDelWhite(uGetTextSafe(tag_href))

    if 'id' in tag_href and len(uLabelDelWhite(tag_href['id'])) > 0:
        ret_anch = tag_href['id']
        if len(foot_title) == 0:
            foot_title = uLabelDelWhite(tag_href['id'])
    elif len(foot_title) == 0:
        err = 'No footnote title for url: ' + url
        foot_title = ''

    if not err and not ret_anch:
        ret_anch = uGenRetAnch(opts, foot_title)

    return err, url, anch, footnote, foot_title, ret_anch, foot_dict


def MainUpdateMemoryCache(opts, url, outdir, footnote, foot_dict, foot_title, foot_dict_list,
                          sect_label_href_list,
                          sect_label_href_list_child, sect_label_href_list_child2):
    """
    Update the cached footnotes and sections kept in memory.
    
    @return: (foot_dict - structure describing a footnote
              sect_dict - structure describing a section)
    """

    sect_dict = {}
    
    if footnote:

        foot_dict_hit = uFindFootDict(foot_title, foot_dict_list)
        
        if not foot_dict_hit and foot_dict:
            foot_dict_list += [foot_dict]

    else:

        # there must be exactly 1 html file in the outdir, otherwise we failed
        # somewhere along the way.
        html_file = uGet1HtmlFile(opts, outdir, True)

        # We merge our child lists with the parent lists at the end of this function
        # when the child list is complete. This creates a more reasonable order in
        # the final output file when each section is appended.
        uMergeSectUniq(opts, sect_label_href_list_child, sect_label_href_list_child2)

        sect_dict = uFindSectHref(opts, url, sect_label_href_list + sect_label_href_list_child)

        if not sect_dict:
        # compute an id for referring to this section
            base_id = MainGenBaseId(opts, url)
            sect_dict = {'html_file': html_file, 'url': url,
                         'foot_title': foot_title, 'base_id': base_id}
        
            sect_label_href_list.append(sect_dict)

    assert foot_dict or sect_dict, "Must have either a footnote or a section at this point. footnote = " + str(footnote)
        

    return foot_dict, sect_dict


def MainGetFootSect(opts, bl, tag_href, foot_dict_list, sect_label_href_list,
                     sect_label_href_list_child):
    """
    Based on an html tag and lists of cached url results resolve an url
    
    @return: (err - any descriptive errors
              footnote - whether the tag points to a footnote or a section
              cache_hit - whether the result had been previously seen
              psym - a symbol indicating what we found to send to stdout for progress)
    """
    
    cache_hit = False

    err, url, anch, footnote, foot_title, ret_anch, foot_dict = \
        MainPickFootVsSect(opts, tag_href)

    if not err and not foot_dict:
        outdir = opts['bodir'] + '/' + os.path.basename(url)

        cache_hit, foot_dict, sect_dict = MainGetCachedFootSect(opts,foot_dict_list,
                            footnote, outdir, foot_title, url, 
                            sect_label_href_list, sect_label_href_list_child)

    if (not err and cache_hit) or foot_dict:
        if cache_hit:
            opts['chits'] = opts['chits'] + 1
        assert foot_dict or sect_dict, \
            "Cache hit did not produce any %s data for url %s" % (
                'footnote' if footnote else 'section', url)
                
    elif not err:
        err, foot_dict, sect_label_href_list_child2 = MainRecursiveCall(opts,
                bl, url, ret_anch, err, footnote, foot_title, foot_dict_list)

        if not err:
            foot_dict, sect_dict = MainUpdateMemoryCache(opts, url, outdir,
                               footnote, foot_dict, foot_title,
                               foot_dict_list, sect_label_href_list,
                               sect_label_href_list_child, sect_label_href_list_child2)

            assert foot_dict or sect_dict, \
                    "No data for url " + url

    if not err:
        # if we have exceeded our depth, their may not be a reference
        err, href = MainGetHref(opts, foot_dict_list, anch, footnote,
                                  foot_title, foot_dict, outdir, sect_dict, url)

        if href[0] == '/':
            assert os.path.exists(href), "Cannot find file %s" % href
        
    if not err:
        MainUpdateHTMLTag(opts, bl, tag_href, ret_anch, footnote,
                           foot_title, href, cache_hit, sect_label_href_list)
    psym = ''
    if not err:

        psym = MainFinalChecksRetPsym(opts, foot_dict_list, footnote,
                                    foot_title, cache_hit, foot_dict)

    return err, footnote, cache_hit, psym 


def MainCheckUrlReachable(opts, bl, ok_i_urls, already_warned_url, tag_href,
                          slink, http404):
    """
    Use wget to test whether we can connect to an URL
    
    @return (slink - removed link count,
             http404 - unreachable link count)
    """
    # the URL is a regular external reference.
    # so we annotate the anchor text with "i" for internet
    #
    # we also cache sucessful hits, and record errors and failures.
    # if we find a failure in our cache we try it again

    psym = ''
    url = tag_href['href']
    err = ''
    url_cache_hit = False
    
    if url in ok_i_urls:
        err = ok_i_urls[url]
        url_cache_hit = True
    else:
        for bad_url_key in LINK_AVOID:
            if bad_url_key in url:
                err = 'Avoiding %s' % bad_url_key
                break

        if not err:
            err = uSysCmd(opts, 'wget -l 0 -t 1 -T 2  --spider "' + url + '"', False)
            opts['wgets'] += 1

    if not err:
        ok_i_urls[url] = ''
        if url_cache_hit:
            opts['chits'] = opts['chits'] + 1

    else:
        ok_i_urls[url] = err
        psym = '!'

    if err:
        # url will appear in the error message, no need to include it again 
        if 'wget' in err:
            err = 'wget failed'
        log_str = 'Not including url (' + psym +'), ' + err
        if url not in log_str:
            log_str = log_str + '\n...' + url
        uPlogExtra(opts, log_str, 2)
        already_warned_url.append(url)

    return err, url_cache_hit, slink, http404, psym


def MainHandleErrs(opts, bl, tag_href, err, ok_i_urls, slink,
                    http404, psym, url_cache_hit, already_warned_url):
    """
    Select a symbol to report progress and log any error messages that occur.
    
    @return: (slink - count of links removed due to similarity to parent or brevity
              http404 - failed internet accesses
              psym - progress symbol)
    """

    url = tag_href['href']

    if not err:
        if tag_href['href'][0:6] == 'http:/' or tag_href['href'][0:7] == 'https:/':

            assert ok_i_urls[url] == '', \
                "Skipped URL. ok_i_urls[url] = " + ok_i_urls[url]
        
            tag1 = bl.new_tag("u")
            tag1.string = '|i|'
            tag_href.contents.append(tag1)
            
            uPlogExtra(opts, 'Verified url (i) '+ url, 3)

            if url_cache_hit:
                psym = 'i'
            else:
                psym = 'I'
        else:
            assert psym, "Expected psym to have been evaluated by now"

    else:
        if err and psym == '!':
            tag_href.name = 'i'
            del tag_href['href']
            http404 += 1 # remove the reference if we cannot reach it
        if 'similar_to_parent' in err:
            FinalReduceSimilarAnchors(opts, bl, url)
            slink += 1
            ok_i_urls[url] = err
            psym = '~'
        elif 'url_failed' in err:
            tag_href.name = 'del'
            del tag_href['href']
            http404 += 1
            ok_i_urls[url] = err
            psym = '!'
        elif 'bad_footnote' in err:
            tag_href.name = 'i'
            del tag_href['href']
            slink += 1
            ok_i_urls[url] = err
            psym = '/'
        else:
            # This shouldn't happen.
            tag_href.name = 'del'
            del tag_href['href']
            ok_i_urls[url] = err
            psym = '*'
            err = 'XXX ' + err

        if url not in already_warned_url or opts['debug'] > 2:
            err += '\n...' + url
            uPlogExtra(opts, 'Dropped footnote (' + psym +'): ' + err, 2)
            already_warned_url.append(url)

    return slink, http404, psym

def MainLoadCache(opts, bl):
    """
    Load Cache data from previous runs stored on our disk
    
    @return (ok_i_urls - a list of Internet addresses and whether they can be reached,
             foot_dict_list - a list of footnotes already processed)
    """

    ok_i_urls = {}
    
    if uGetFlistFromDir(opts['base_bodir'] +
                          '/footnotes/','Reachable_Internet_Links','.json', False):

        fp = open(opts['base_bodir'] + '/footnotes/' + 'Reachable_Internet_Links.json', 'r')
        ok_i_urls = json.load(fp)
        fp.close()

    # if we are asked to clean up our cache, go through the list of previously
    # visited urls and discard those that were the result of internet errors
    # Keep previously verified urls, or urls that were known to be like the parent
    if opts['clean_cache'] >= 1:
        old_ok_i_urls = ok_i_urls
        ok_i_urls = {}
        for item in old_ok_i_urls.items():
            # retry certain errors, but not all errors
            if (item[1] == '' or 'bad_footnote' in item[1]):
                ok_i_urls[item[0]] = item[1]
            # if a footnote was similar to its parent in the past this won't change.
            # We can't totally ignore this error, we need to reduce again
            if 'similar_to_parent' in item[1]:
                FinalReduceSimilarAnchors(opts, bl, item[0])
                ok_i_urls[item[0]] = item[1]


    # footnotes should be numbered in sequence. Keep loading until
    # we get a failure. Not sure why we incremented footi in the presence
    # of a failure, but that is what seems to have happened. For some reason
    # not all footnotes are stored, be tollerant of missing ones.
    #
    # Better strategy would be to get dir listing rather than guessing the names.
    
    foot_dict_list = []
    
    foot_file_list = uGetFlistFromDir(opts['base_bodir'] + '/footnotes/',W2EBRI,'.json', False)
        
    for foot_file in foot_file_list:
        fp = open(foot_file, 'r')
        foot_dict = json.load(fp)
        fp.close()
        foot_dict_list += [foot_dict]


    if len(foot_dict_list) > 0 or len(ok_i_urls) > 0:
        uPlog(opts, "Loaded %d footnotes and %d urls from cache" % 
               (len(foot_dict_list), len(ok_i_urls)))

    return ok_i_urls, foot_dict_list 

def MainNotes(opts, bl):
    """
    Entry point for collecting articles and footnotes.
    """
    
    i = 0
    sect_label_href_list = []
    sect_label_href_list_child = []
    slink = 0
    http404 = 0
    im_all = 0
    already_warned_url = []
    
    uPlog(opts,'')
    ok_i_urls, foot_dict_list = MainLoadCache(opts, bl) 

    st_time = time.time()
    
    uPlog(opts, 'Collecting Footnotes (F), Articles (A), and Internet Links (I)')
    sys.stdout.flush()
    uPlogExtra(opts, '', 1)

    for tag_href in bl.find_all(lambda x: uHrefRemote(x)):
        im_all += 1
    
    p_total_est_time = im_all / 3.0
    
    for tag_href in bl.find_all(lambda x: uHrefRemote(x)):

        if not tag_href.has_attr('href'):
            # this function may remove 'href' fields during the loop
            # so need to confirm that there still really is an 'href'            
            continue

        err, url_cache_hit, slink, http404, psym = MainCheckUrlReachable(opts, bl,
              ok_i_urls, already_warned_url, tag_href, slink, http404)
        
        if not err and uUrlOk(opts, tag_href['href'], opts['footsect_name']):

            err, footnote, cache_hit, psym = MainGetFootSect(opts,
                           bl, tag_href, foot_dict_list, sect_label_href_list, 
                           sect_label_href_list_child)

            if not err:      # Count successful footnotes and reset progress bar

                if footnote:
                    opts['footi'] += 1 
                if not footnote and not cache_hit:
                    uPlog(opts, '----------' + opts['footsect_name'] + '------- cont...')
                    if i % 25 != 0:
                        p_total_est_time = uPrintProgress(opts, st_time, i, 
                                                      im_all, p_total_est_time)

        slink, http404, psym = MainHandleErrs(opts, bl, tag_href, err, ok_i_urls,
                                     slink, http404, psym, url_cache_hit, already_warned_url)
                
        assert(psym), "Should not happen. psym should be defined at this point"

        if i % 25 == 0:
            p_total_est_time = uPrintProgress(opts, st_time, i,
                                              im_all, p_total_est_time)

        uPlogNr(opts, psym)
        i = i + 1
        sys.stdout.flush()

    uPlogNr(opts, '\n')  # we are done, go back to regular printing
    fp = open(opts['base_bodir'] + '/footnotes/' + 'Reachable_Internet_Links.json', 'w')
    json.dump(ok_i_urls, fp)
    fp.close()
    
    uMergeSectUniq(opts, sect_label_href_list, sect_label_href_list_child)
    
    return [sect_label_href_list, foot_dict_list, slink, http404]


def MainWelcomeMsg(opts, st_time):
    """
    Print the welcom message for generating sections
    """

    uPlog(opts, '')
    uPlog(opts, '---------------------------------------------')
    uPlog(opts, '==> Downloading Wikibook "' + opts['footsect_name'] + '"')
    uPlog(opts, "Started at", time.asctime(time.localtime(st_time)))
    uPlog(opts, "Searching:", opts['url'])
    if opts['parent']:
        uPlog(opts,'Parent = "' + opts['parent'] + '"')

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


def MainSectionCreate(opts, st_time, bl, section_bname):

    st_time = time.time()
    im_tot = 0
    convert = 0
    slink = 0
    http404 = 0
    foot_dict_list = []
    foot_dict = {}

    StartupReduceTags(opts, bl, section_bname)
    im_tot, convert = PicGetImages(opts, bl) # easy...
    foot_dict_loc_list = LocalReuse(opts, bl)
    [sect_label_href_list, foot_dict_list, slink, http404] = MainNotes(opts, bl)

    foot_dict_list += foot_dict_loc_list


    sect_label_href_list = FinalMergeFootSectTOC(opts, st_time, bl, section_bname,
            im_tot, convert, slink, http404, foot_dict_list, sect_label_href_list)

    uSaveFile(opts, opts['bodir'] + '/' + section_bname,
              bl.prettify(formatter="html").splitlines(True))
    
    return foot_dict_list, sect_label_href_list

def Main(opts):
    
    st_time = time.time()
    foot_dict_list = []
    foot_dict = {}
    sect_label_href_list = []
    
    opts['footsect_name'] = opts['footsect_name']
    opts['bodir'] = opts['bodir']
        
    assert not opts['footnote'], "Main does not generate footnotes, only sections. See GenTextGetFootNote" 

    uClean(opts)

    if opts['parent'] == '':
        opts['base_url'] = opts['url']
        opts['base_bodir'] = opts['bodir']

    err, bl, section_bname = uGetHtml(opts)
    
    if err:
        return err, [], []

    # Compare this section sketch to parents. Fail if they are too similar.    
    opts['my_sketch'] = SketchPage(bl)
    i_am_my_parent = SketchVsMySketch(opts['parent_sketch'], 
                                                opts['my_sketch'])

    if i_am_my_parent:
        return 'similar_to_parent: ' + i_am_my_parent, None, None

    MainWelcomeMsg(opts, st_time)
    
    opts['section_bname'] = section_bname
    
    foot_dict_list, sect_label_href_list = MainSectionCreate(opts, st_time, bl, section_bname)

    return err, foot_dict_list, sect_label_href_list
