



def FinalPrintArticleStats(opts, im_tot, convert, sect_label_href_list, foot_dict_list,
                      slink, http404, ilink, blink):

    uPlog(opts, "\nFound", str(im_tot), "Figures,", "Converted", str(convert), "Figures")

    sfnotes = "Extracted %d Footnotes." % len(foot_dict_list)
    
    if sect_label_href_list:
        sfnotes += " Identified %d Subsections via %s heuristic." %\
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


def FinalPrintStats (opts, bl, im_tot, convert, sect_label_href_list, foot_dict_list,
                     slink, http404, toc_links, old_toc, st_time, ipath): 

    ilink = 0
    blink = 0
    
    for tag_href in bl.find_all(lambda x: Foot1HrefAll(x)):
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
    uPlog(opts, "Conversion took",str_smh(time.time() - st_time))
    uPlog(opts, '')
    uPlog(opts, "wrote " + ipath)
    uPlog(opts, "==> Done")
    uPlog(opts, '')


def FinalAddSections(opts, bl, sect_label_href_list):
    
    if not sect_label_href_list:
        return
    
    head = bl.find('div', class_='mw-content-ltr')
    
    assert head, 'Unable to find root of html text, mw-parser-output'
    
    head = list(head.contents)[0]
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
        main_sketch = MainSketchPage(bl)
        sect_sketch = MainSketchPage(sl)
        similar = MainParentSketchVsMySketch(main_sketch, sect_sketch)
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
            
    AddReduceHtmlRefs2Anchors(opts, bl, final_section_list)

    AddReduceHtmlRefs2AnchorsFinal(opts, bl)
    
    return final_section_list

def FinalSummaries(opts, bl, foot_dict_list):
    

    if not foot_dict_list:
        return

    #head = bl.find('div', class_='mw-parser-output')
    head = bl.find('div', class_='mw-content-ltr')
    
    assert head, 'Unable to find root of html text, mw-parser-output'
    
    head = list(head.contents)[0]
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
    
    foot_dict_list.sort(key = lambda x: x['foot_title'])
    
    for item in foot_dict_list:
        # if we number our backlinks then they too are footnotes... ug. 
        num = '[' + item['ret_anch'].split('_')[2] +']'
        ftext = item['short_foot'].replace('<p><a','<p>' + num + '<a')
        
        short_foot = BeautifulSoup(ftext, 'html.parser')
        foot_note_section.append(short_foot)

    top_note = bl.new_tag('h2', id='wiki2epub_' + opts['footsect_name'] + '_notes')
    top_note.string='Notes'
    top_note['class'] = 'section'
    foot_note_section.append(top_note)
    
    for item in foot_dict_list:
        
        foot_long =''
        for par in item['long_foot']:
#            foot_long = clean_char_app(foot_long, par)
#            foot_long = uCleanChars(opts, foot_long) + uCleanChars(opts, par)
            foot_long = foot_long + par

        note = BeautifulSoup(foot_long, 'html.parser')
        foot_note_section.append(note)

def FinalAddDebugHeadings(opts, bl):

    """
    @summary: Add debug headings prior to entries here so they appear in TOC
    """
    
    if opts['debug'] == 0:
        return

    head = bl.find('div', class_='mw-content-ltr')
    assert head, 'Unable to find root of html text, mw-parser-output'
    head = list(head.contents)[0]
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
    @summary: The dubug log is kept in a file named wiki_log, include it in the ebook
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
                dbg_data2.string += uCleanChars(opts, line)
        
        dbg_section.append(dbg_data2)
