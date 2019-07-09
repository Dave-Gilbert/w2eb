
from w2ebUtils import *

def Foot3RaiseAnchor(tag_href, ret_anch):
    """
    @summary: Raise the anchor to a location shortly before the reference
    
    @note: Kindle often needs an id to appear a little before the text that
           it anchors. Put return id in previous sibling or parent if possible.

    """

    if (tag_href.previous_sibling and not isinstance(tag_href.previous_sibling, NavigableString) and 
        not tag_href.previous_sibling.has_attr('id')):
        tag_href.previous_sibling['id'] = ret_anch
    elif not tag_href.parent.has_attr('id'):
        tag_href.parent['id'] = ret_anch
    else:
        tag_href['id'] = ret_anch


def Foot3GenBaseId(opts, url):
    """
    @summary: given either an url or an html file compute the base_id used to locate pages
    """
    
    
    htp = 'https:/'
    if url[:len(htp)] != htp:
        url.replace(opts['base_bodir'],opts['base_url'])  
    base_id = url[len(htp):].replace(' ','_').replace('/','_').replace('.','_')
    base_id = W2EBID + urllib.quote(base_id)

    return base_id

def Foot2UpdateHTMLTag(opts, bl, tag_href, ret_anch, footnote, foot_title,
                        href, cache_hit, sect_label_href_list):
    """
    @summary: - Modify footnote tag_href. For Sections build up list of href details.

                
    We add the return anchor to our href tag for both sections and footnotes.
    
    For footnotes we create a number in parenthesis which we append to the anchor.
    We cheat a little and use an underlined html tag so it matches the underline
    for the hyperlinked url.
    
    We downloaded a section if ( opts['base_url'] in url and opts['depth'] > 0)
    In that case we keep a note of the html_file, url, and section name. We
    will clean up the references later when all the sections are appended.
    
    """

    if opts['depth'] == 0 and href[0:4] == 'http':
        # XXX I think we just skip this... it will be handled later,
        # but maybe it should be handled here?
        return

    if footnote:

        tag_num = bl.new_tag("i")
        num = ' [' + ret_anch.split('_')[2] +']'  # XXX compute the ind from ret_anch
        tag_num.string = num
        # if we append the number to href then it becomes part of the link and
        # kindle *may* interpret it as a footnote. This doesn't work reliably,
        # I'm not sure how to end the footnote. Until this is fixed we will 
        # insert tag1 after tag_href. It should look the same but behave differently.
        #
        # Seems that changing the brackets may be the only way to disable this behaviour.
        if False:
            tag_href.append(tag_num) # include num as part of link
        else:
            tag_href.insert_after(tag_num)

        Foot3RaiseAnchor(tag_href, ret_anch)

    else:
        # we don't do anything special for section hrefs (should we?)
        None
    
    tag_href['href'] = href


def Foot2FinalChecksRetPsym(opts, foot_dict_list, footnote, foot_title, cache_hit, foot_dict):

    if footnote and opts['depth'] > 0:
        assert foot_title and FindFootDict(foot_title, foot_dict_list) , \
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



def Foot2PickFootVsSect(opts, tag_href):
    """
    @summary: Decide whether the tag will be processed as a section or a footnote
    
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
    
    url = tag_href['href']

    footnote = True

    if opts['depth'] > 0:
    
        if (opts['stype'] == 'url' and opts['base_url'] in url):
            uPlogExtra(opts, "Identified SubSection based on url match.\n%s < %s\n" %
                      (opts['base_url'],  url),2)
            footnote = False
        elif (opts['stype'] == 'bookname' and opts['booknm'] in url):
            uPlogExtra(opts, "Identified SubSection based on book name match.\n%s < %s\n" %
                      (opts['booknm'],  url),2)
            footnote = False
        elif (opts['stype'] == 'bookword'):
            
            for word in opts['booknm'].split('_'):
                if len(word) > 4 and word in url:
                    uPlogExtra(opts, "Identified SubSection based on book word match.\n%s < %s\n" %
                              (word,  url),2)
                    footnote = False
                    break

    
    if '#' in url:
        anch = url.split('#')[1]
        url = url.split('#')[0]
    foot_title = LabelDelWhite(uCleanChars(opts, get_text_safe(tag_href)))
    if 'id' in tag_href and len(LabelDelWhite(tag_href['id'])) > 0:
        ret_anch = tag_href['id']
        if len(foot_title) == 0:
            foot_title = LabelDelWhite(uCleanChars(opts, tag_href['id']))
    elif len(foot_title) == 0:
        err = 'No footnote title for url: ' + url
        foot_title = ''
    else:
        ret_anch = W2EBRI + '%d_%s' % (opts['footi'], LabelAnchSuff(foot_title))

#    if not err:
#        assert ret_anch[-1] != '_', "Badly formed return anchor: ret_anch = " +\
#             ret_anch + ", foot_title = " + foot_title

    return err, url, anch, footnote, foot_title, ret_anch


def Foot2UpdateMemoryCache(url, outdir, footnote, foot_dict, foot_title, foot_dict_list,
                          sect_label_href_list,
                          sect_label_href_list_child, sect_label_href_list_child2):
    """
    @summary: Update the cached footnotes and sections kept in memory.
    
    @return: (foot_dict - structure describing a footnote
              sect_dict - structure describing a section)
    """

    sect_dict = {}
    
    if footnote:

        foot_dict_hit = FindFootDict(foot_title, foot_dict_list)
        
        if not foot_dict_hit and foot_dict:
            foot_dict_list += [foot_dict]

    else:

        # there must be exactly 1 html file in the outdir, otherwise we failed
        # somewhere along the way.
        html_file = uGet1HtmlFile(opts, outdir, True)

        # We merge our child lists with the parent lists at the end of this function
        # when the child list is complete. This creates a more reasonable order in
        # the final output file when each section is appended.
        MergeSectUniq(opts, sect_label_href_list_child, sect_label_href_list_child2)

        sect_dict = FindSectHref(opts, url, sect_label_href_list + sect_label_href_list_child)

        if not sect_dict:
        # compute an id for referring to this section
            base_id = Foot3GenBaseId(opts, url)
            sect_dict = {'html_file': html_file, 'url': url,
                         'foot_title': foot_title, 'base_id': base_id}
        
            sect_label_href_list.append(sect_dict)

    assert foot_dict or sect_dict, "Must have either a footnote or a section at this point. footnote = " + str(footnote)
        

    return foot_dict, sect_dict



def Foot1GetFootSect(opts, bl, tag_href, foot_dict_list, sect_label_href_list,
                     sect_label_href_list_child):
    """
    @summary: based on an html tag and lists of cached url results resolve an url
    
    @return: (err - any descriptive errors
              footnote - whether the tag points to a footnote or a section
              cache_hit - whether the result had been previously seen
              psym - a symbol indicating what we found to send to stdout for progress)
    """
    
    cache_hit = False

    err, url, anch, footnote, foot_title, ret_anch = Foot2PickFootVsSect(opts, tag_href)

    if not err:
        outdir = opts['bodir'] + '/' + os.path.basename(url)

        cache_hit, foot_dict, sect_dict = Foot2GetCachedFootSect(opts,foot_dict_list,
                            footnote, outdir, foot_title, url, 
                            sect_label_href_list, sect_label_href_list_child)

    if not err and cache_hit:
        opts['chits'] = opts['chits'] + 1
        assert foot_dict or sect_dict, \
            "Cache hit did not produce any %s data for url %s" % (
                'footnote' if footnote else 'section', url)
                
    elif not err:
        if opts['depth'] > 0:
            err, foot_dict, sect_label_href_list_child2 = Foot2RecursiveCall(opts,
                    bl, url, ret_anch, err, footnote, foot_title, foot_dict_list)

            if not err:
                foot_dict, sect_dict = Foot2UpdateMemoryCache(url, outdir, footnote, foot_dict, foot_title,
                                   foot_dict_list, sect_label_href_list,
                                   sect_label_href_list_child, sect_label_href_list_child2)

                assert foot_dict or sect_dict, \
                        "No data for url " + url

    if not err:

        # if we have exceeded our depth, their may not be a reference
        
        err, href = Foot12GetHref(opts, foot_dict_list, anch, footnote,
                                  foot_title, foot_dict, outdir, sect_dict, url)

        if href[0] == '/':
            assert os.path.exists(href), "Cannot find file %s" % href
        
    if not err:
        Foot2UpdateHTMLTag(opts, bl, tag_href, ret_anch, footnote,
                           foot_title, href, cache_hit, sect_label_href_list)
    psym = ''
    if not err:
        
        psym = Foot2FinalChecksRetPsym(opts, foot_dict_list, footnote,
                                    foot_title, cache_hit, foot_dict)

    return err, footnote, cache_hit, psym 


def Foot1CheckUrlReachable(opts, bl, ok_i_urls, already_warned_url, tag_href,
                          slink, http404):
    """
    @summary: - Use wget to test whether we can connect to an URL
    
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


def Foot1UrlOk(opts, url, footsect_name):
    """
    @summary: Limit our search to wikipedia articles
    
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


def Foot2HrefOk(tag_href, exclude_internal):
    """
    @summary: Verify that soup tag is an anchor with an href and other properties
    
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


def Foot1HrefRemote(tag_href):
    """
    @summary: True if tag is an anchor that refers to a remote footnote or section
    """
    return Foot2HrefOk(tag_href, True)


def Foot1HrefAll(tag_href):
    """
    @summary: True if tag is an anchor that refers to text in this page or elsewhere
    """
    return Foot2HrefOk(tag_href, False)


def Foot1HandleErrs(opts, bl, tag_href, err, ok_i_urls, slink,
                    http404, psym, url_cache_hit, already_warned_url):
    """
    @summary: Select a symbol to report progress and log any error messages that occur.
    
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
            Foot2ReduceSimilarAnchors(opts, bl, url)
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


def Foot1LoadCache(opts, bl):
    """
    @summary: Load Cache data from previous runs stored on our disk
    
    @return (ok_i_urls - a list of Internet addresses and whether they can be reached,
             foot_dict_list - a list of footnotes already processed)
    """

    ok_i_urls = {}
    
    if uGetFlistFromDir(opts['base_bodir'] +
                          '/footnotes/','Reachable_Internet_Links','.json', False):

        fp = open(opts['base_bodir'] + '/footnotes/' + 'Reachable_Internet_Links.json', 'r')
        ok_i_urls = json.load(fp)
        fp.close()

    if opts['clean_html']:
        old_ok_i_urls = ok_i_urls
        ok_i_urls = {}
        for item in old_ok_i_urls.items():
            # retry certain errors, but not all errors
            if (item[1] == '' or 'bad_footnote' in item[1]):
                ok_i_urls[item[0]] = item[1]
            # if a footnote was similar to its parent in the past this won't change.
            # We can't totally ignore this error, we need to reduce again
            if 'similar_to_parent' in item[1]:
                Foot2ReduceSimilarAnchors(opts, bl, item[0])
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

def FootNotes(opts, bl):
    
    i = 0
    sect_label_href_list = []
    sect_label_href_list_child = []
    slink = 0
    http404 = 0
    im_all = 0
    already_warned_url = []
    
    uPlog(opts,'')
    ok_i_urls, foot_dict_list = Foot1LoadCache(opts, bl) 

    st_time = time.time()
    
    uPlog(opts, 'Collecting Footnotes (F), Articles (A), and Internet Links (I)')
    sys.stdout.flush()
    uPlogExtra(opts, '', 1)

    for tag_href in bl.find_all(lambda x: Foot1HrefRemote(x)):
        im_all += 1
    
    p_total_est_time = im_all / 3.0
    
    for tag_href in bl.find_all(lambda x: Foot1HrefRemote(x)):

        if not tag_href.has_attr('href'):
            # this function may remove 'href' fields during the loop
            # so need to confirm that there still really is an 'href'            
            continue

        if tag_href['href'][0] == '#':
            # assume that the relative link is fine... we could verify it,
            # but for now just leave it there.
            continue

        # tag refers to something, if it is an okay url then maybe fetch the data

        err, url_cache_hit, slink, http404, psym = Foot1CheckUrlReachable(opts, bl,
              ok_i_urls, already_warned_url, tag_href, slink, http404)
            
        if not err and Foot1UrlOk(opts, tag_href['href'], opts['footsect_name']):

            err, footnote, cache_hit, psym = Foot1GetFootSect(opts,
                           bl, tag_href, foot_dict_list, sect_label_href_list, 
                           sect_label_href_list_child)

            if not err:      # Count successful footnotes and reset progress bar

                if footnote:
                    opts['footi'] += 1 
                if not footnote and not cache_hit:
                    uPlog(opts, '----------' + opts['footsect_name'] + '------- cont...')
                    if i % 25 != 0:
                        p_total_est_time = print_progress(opts, st_time, i, 
                                                      im_all, p_total_est_time)

        slink, http404, psym = Foot1HandleErrs(opts, bl, tag_href, err, ok_i_urls,
                                     slink, http404, psym, url_cache_hit, already_warned_url)
                
        assert(psym)

        if i % 25 == 0:
            p_total_est_time = print_progress(opts, st_time, i,
                                              im_all, p_total_est_time)

        uPlogNr(opts, psym)
        i = i + 1
        sys.stdout.flush()

    uPlogNr(opts, '\n')  # we are done, go back to regular printing
    fp = open(opts['base_bodir'] + '/footnotes/' + 'Reachable_Internet_Links.json', 'w')
    json.dump(ok_i_urls, fp)
    fp.close()
    
    MergeSectUniq(opts, sect_label_href_list, sect_label_href_list_child)
    
    return [sect_label_href_list, foot_dict_list, slink, http404]