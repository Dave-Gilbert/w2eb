"""
@summary:      W2EB - Final: Assemble the final elements of the ebook
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

import time

from w2ebUtils import *

from bs4 import BeautifulSoup

from w2ebTOC import TocMake 
from w2ebTOC import TocRemoveOldToc
from w2ebSketch import SketchPage
from w2ebSketch import SketchVsMySketch

def FinalPrintArticleStats(opts, im_tot, convert, sect_label_href_list,
                           foot_dict_list, slink, http404, ilink, blink):
    """
    Print statistics for figures, footnotes, subsections, links and network access.

    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param im_tot: Total number of images
    @param convert: Total number of image conversions
    @param sect_label_href_list: List of sections by label and href
    @param foot_dict_list: List of footnotes represented by dictionaries
    @param slink: Number of bad links removed, often due to similarity with parent
    @param http404: Number of unreachable links
    @param ilink: Internet references
    @param blink: Book links, or internal page references
    """

    uPlog(opts, "\nFound", str(im_tot), "Figures,", "Converted", str(convert), "Figures")

    sfnotes = "Extracted %d Footnotes" % len(foot_dict_list)
    
    nc = FinalNoteCount(foot_dict_list)
    
    if nc:
        sfnotes += ", %d notes" % nc
        
    if opts['stats_r']:
        sfnotes += ", %d recycled footnotes." % opts['stats_r']  
    else:
        sfnotes += '.'

    if sect_label_href_list:
        sfnotes += "\nIdentified %d Subsections via %s heuristic." %\
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


def FinalHrefAll(tag_href):
    """
    True if tag is an anchor that refers to text in this page or elsewhere
    
    @param tag_href: B Soup object representing a tag with an "href" attribute
    
    """
    return uHrefOk(tag_href, False)

def FinalPrintStats(opts, bl, im_tot, convert, sect_label_href_list, foot_dict_list,
                     slink, http404, toc_links, old_toc, st_time, ipath): 
    """
    Print main parent statistics, compute a few simple stats, like ilink and blink. 
    
    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
    @param im_tot: Total number of images
    @param convert: Total number of image conversions
    @param sect_label_href_list: List of sections by label and href
    @param foot_dict_list: List of footnotes represented by dictionaries
    @param slink: Number of bad links removed, often due to similarity with parent
    @param http404: Number of unreachable links
    @param toc_links: Table of contents links to sections
    @param old_toc: Number of told table of contents removed
    @param st_time: Start time
    @param ipath: Output file path
    """

    ilink = 0
    blink = 0
    
    for tag_href in bl.find_all(lambda x: FinalHrefAll(x)):
        if tag_href['href'][0:4] == 'http':            
            ilink += 1
        else:
            blink += 1

    FinalPrintArticleStats(opts, im_tot, convert, sect_label_href_list, foot_dict_list, slink,
                          http404, ilink, blink)
    if opts['parent'] == '':
        ostr = 'Table of Contents Entries = ' + str(toc_links)
        if old_toc > 1:
            ostr += ', Removed %d old TOC Tables' % old_toc
        uPlog(opts, ostr)
        uPlog(opts, "\nFinished at " + time.asctime(time.localtime(time.time())))
        uPlog(opts, "Conversion took", uStrTimeSMH(time.time() - st_time))
        
    uPlog(opts, '')
    uPlog(opts, "wrote " + ipath)
    uPlog(opts, "==> Done")
    uPlog(opts, '')


def FinalAddSections(opts, bl, sect_label_href_list):
    """
    Add the collected sections to the end of the book
    
    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
    @param sect_label_href_list: List of sections by label and href
    
    @note: 
    
    The order of sect_label_href_list is important, and determined during book
    traversal. The tree of sections is flattened using a breadth first search.
    This means that all the references to any article appear in order after that
    article, even if those articles have their own subarticles. 
    """
    
    if not sect_label_href_list:
        return
    
    head = bl.find('div', class_='mw-parser-output')
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
        main_sketch = SketchPage(bl)
        sect_sketch = SketchPage(sl)
        similar = SketchVsMySketch(main_sketch, sect_sketch)
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
            
    FinalReduceHtmlRefs2Anchors(opts, bl, final_section_list)

    FinalReduceHtmlRefs2AnchorsFinal(opts, bl)
    
    return final_section_list


def FinalNoteCount(foot_dict_list):
    """
    Count the number of full notes.

    @param foot_dict_list: List of footnotes represented by dictionaries

    @note: Not every foot_dict includes a long form note. Only some
    will. Count those that do.
    """
    tnotes = 0
    for foot_dict in foot_dict_list:
        if foot_dict['long_foot']:
            tnotes += 1
            
    return tnotes

def FinalFixFirstRefLabel(bl, foot_dict_list): 
    """
    Append 'a' for multi reference footnotes

    @param bl:  Beautiful Soup representation of an HTML web page.
    @param foot_dict_list: List of footnotes represented by dictionaries

    @note: When we generate a footnote for the first time we don't know
    if it will have multiple references, so we just guess that it won't.
    This function finds those foonotes, and appends a 'a' to their name.
    """
    for foot_dict in foot_dict_list:
        if len(foot_dict['ret_anch_all']) > 1:
            ref = '#' + foot_dict['id_anch'] + '_foot'
            tag_href = bl.find('a', href=ref)
            if not tag_href:
                print "PPP", "Couldn't find one of our own footnotes " + ref
            else:
                if tag_href.string:
                    tag_href.string = tag_href.string.replace(']','a]')
                    
                else:
                    tag_i = tag_href.find('i')
                    if tag_i:
                        if tag_i.string:
                            tag_i.string = tag_i.string.replace(']','a]')
                        else:
                            print "PPP", "Couldn't find Italic text for footnote" + ref
                            
                    else:
                        print "PPP", "Couldn't find text for footnote" + ref


def FinalBackLinks(foot_dict):
    """
    Generate the backlinks for each footnote.

    @param foot_dict: Dictionary storing details for notes and footnotes

    @note: Most footnotes will be referred to once, but it is not unusual
    for a footnote to have multiple referents. We need to provide an
    appropriate backlink mechanism so we can return to any one of them.
    
    @return: an html string with a list of links
    """

    if len(foot_dict['ret_anch_all']) == 1:
        # common case:
        ret_anch = foot_dict['ret_anch_all'][0]
        blstr = ' ... <a href="' + '#' + ret_anch + '">back</a>'
    else:
        # complicated case:
        blstr = ' ... back ['
        sep = ''
        for ret_anch in foot_dict['ret_anch_all']:
            r_id = ret_anch[-1]
            blstr += sep
            blstr += '<a href="' + '#' + ret_anch + '">'
            blstr += r_id + '</a>'
            sep = ', '
            
        blstr += ']'

    return blstr


def FinalAddFootnotes(opts, bl, foot_dict_list):
    """
    Append the foot note dictionary list at the end of the book.
    
    @param opts: global parameters
    @param bl: beautiful soup html structure
    @param foot_dict_list: A list of footnotes in dictionary format
        
    """

    if not foot_dict_list:
        return

    head = bl.find('div', class_='mw-parser-output')
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
    
    foot_dict_list.sort(key = lambda x: x['foot_title'].lower())
    
    for foot_dict in foot_dict_list:
        # if we number our backlinks then they too are footnotes... ug. 
        num = '[' + foot_dict['id_anch'].split('_')[2] +']'
        ftext = foot_dict['short_foot'].replace('<p><a','<p>' + num + '<a')
        
        ftext = ftext.replace(W2EB_BLM, FinalBackLinks(foot_dict))
        
        short_foot = BeautifulSoup(ftext, 'html.parser')
        foot_note_section.append(short_foot)

    top_note = bl.new_tag('h2', id='wiki2epub_' + opts['footsect_name'] +
                          '_notes')

    if FinalNoteCount(foot_dict_list):

        top_note.string='Notes'
        top_note['class'] = 'section'
        foot_note_section.append(top_note)
        
        for foot_dict in foot_dict_list:
            
            foot_long =''
            for par in foot_dict['long_foot']:
                par = par.replace(W2EB_BLM, FinalBackLinks(foot_dict))
                foot_long = foot_long + par
    
            note = BeautifulSoup(foot_long, 'html.parser')
            foot_note_section.append(note)


def FinalAddDebugHeadings(opts, bl):
    """
    Add debug headings prior to entries here so they appear in TOC

    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.

    """
    
    if opts['debug'] == 0:
        return

    head = bl.find('div', class_='mw-parser-output')
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


def FinalAddDebugEntries(opts, bl):
    """
    The dubug log is kept in a file named wiki_log, include it in the ebook

    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
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
                dbg_data2.string += uCleanChars(line)
        
        dbg_section.append(dbg_data2)
        

def FinalReduceSimilarAnchors(opts, bl, url):
    """
    Find all references to URL and make them local, preserving anchors

    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
    @param url: The references that we are looking for 
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


def FinalReduceHtmlRefs2Anchors(opts, bl, final_section_list):
    """
    Find all references to html files and convert them to anchors
    
    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
    @param final_section_list: List of sections by label and href, final version
 
    
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
                
                sect_dict = uFindSectHref(opts, href, final_section_list)
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
                          (why, tag_href['href'], new_id), 3)
            
                tag_href['href'] = '#' + new_id



def FinalReduceHtmlRefs2AnchorsFinal(opts, bl):
    """
    Find all references to html files and convert them to anchors or remove them

    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param bl:  Beautiful Soup representation of an HTML web page.
 
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


def FinalMergeFootSectTOC(opts, st_time, bl, section_bname, im_tot, convert,
                          slink, http404, foot_dict_list, sect_label_href_list):
    """
    Merge the main text with footnotes, sections, TOC, and debug logs.

    @param opts: Dictionary of common CLI parameters. See StartupGetOptions()
    @param st_time: Start time
    @param bl:  Beautiful Soup representation of an HTML web page.
    @param section_bname: Basename for the section, i.e. filename w.o. path
    @param im_tot: Total number of images
    @param convert: Total number of image conversions
    @param slink: Number of bad links removed, often due to similarity with parent
    @param http404: Number of unreachable links
    @param foot_dict_list: List of footnotes represented by dictionaries
    @param sect_label_href_list: List of sections by label and href

    @return: (sect_label_href_list - a list of sections)
    """

    if opts['parent']:
        uPlog(opts, '=============================================')
    else:
        uPlog(opts, '=================Finalizing==================')
    toc_links = 0
    old_toc = 0
    if opts['parent'] == '':
        while TocRemoveOldToc(opts, bl) == '':
            old_toc += 1

        final_sect_label_href_list = FinalAddSections(opts, bl, sect_label_href_list)
        FinalAddFootnotes(opts, bl, foot_dict_list)
        FinalFixFirstRefLabel(bl, foot_dict_list) 
        
        FinalAddDebugHeadings(opts, bl)
        toc_links = TocMake(opts, bl)
        sect_label_href_list = final_sect_label_href_list
    FinalPrintStats(opts, bl, im_tot, convert, sect_label_href_list,
                    foot_dict_list, slink, http404, toc_links, old_toc,
                    st_time, opts['footsect_name'] + '/' + section_bname)
    if opts['parent'] == '':
        FinalAddDebugEntries(opts, bl)
    
    return sect_label_href_list


