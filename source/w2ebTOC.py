

from bs4 import NavigableString


from w2ebUtils import *
from w2ebConstants import *



def TocShortLabel(heading_str):
        
    rval = heading_str.strip()

    if heading_str.count(' ') < 6 and len(heading_str) < 40:
        None    

    elif len(heading_str) < 25:
        rval = heading_str

    else:
        
        trail = ' ...'
        
        for i in range(25, len(heading_str)):
            
            # if we find some sort of end skip the ...
            if heading_str[i] in Punc1 + Punc2:
                trail = ''
                i += 1
                break

            # not an end but lets not get anything else started
            if heading_str[i] in Punc3:
                break
            
            # anything other than a-z will do
            if i > 40 and not heading_str[i].isalpha():
                break
            
            # enough
            if i > 60:
                break
    
        if len(heading_str) == i:
            trail =''
        rval = heading_str[0:i] + trail
    
    return rval


def TocGetH1H2(hlist, hdlist, curr, head):
    """
    @summary:  verify curr and if okay add to our list of tags.
    """
       
    if isinstance(curr, NavigableString):
        return [hlist, hdlist]
    
    # Don't include the old TOC label in our new TOC
    # We are going to remove this, so we don't want a dead link
    if curr == head:
        return [hlist, hdlist]        

    if (curr.name != 'h1' and 
        curr.name != 'h2'):
        return [hlist, hdlist]
    
    if not curr.has_attr('id'):
        
        if not uGetTextSafe(curr).strip():
            # with no text and no id, this isn't really anything
            return
        curr['id'] = 'toc_heading_' + str(len(hdlist)) 
        
        # return [hlist, hdlist]  XXX why did we skip these?
        
    if curr['id'] not in hdlist:

        curr_str = uGetTextSafe(curr).strip()

        if curr_str == "":
            curr_str = curr['id'].replace('_',' ').title()
            curr_str = curr_str.strip()
        
        entry = {'lvl': curr.name,
                 'heading': curr_str,
                 'tag':curr}

        # Makes it easy for Calibre to build a TOC
        # but Kindle makes a mess when there are too many levels
        # Calibre doesn't seem to know how to make levels colapse. 
        # That might be an epub / mobi problem. 
        if curr.name == 'h1':        
            curr['class'] = 'chapter'

        hlist += [entry]
        hdlist += [curr['id']]

    return [hlist, hdlist]

def TocMakeAndLinkTags(opts, bl, toc_list, hlist):
    
    # add the toc items
    
    lvl = 'h1'
    chapt_list = toc_list
    for htag in hlist:
        old_lvl = lvl
        tag = htag['tag']
        lvl = str(htag['lvl'])
        if lvl == 'h2' and old_lvl != 'h2':
            chapt_list = bl.new_tag('ul')
            toc_list.append(chapt_list)
        elif lvl == 'h1':
            chapt_list = toc_list
        else:
            None
        # do nothing, chap_list is correctly set
        li = bl.new_tag('li')
        chapt_list.append(li)
        text = bl.new_tag('a', href='#' + tag['id'])

        text.append(uLabelDelWhite(TocShortLabel(htag['heading'])))
        li.append(text)
        
        uPlogExtra(opts, "Toc - adding " + lvl + ' ' + TocShortLabel(htag['heading']), 3)

def TocCandidate(tag):
    
    toc_headings = ['table_of_contents', 'table of contents', 'contents', 'toc']
    
    if tag.name == 'div' and tag.has_attr('class') and tag['class'] == 'toc':
        return True
    if tag.name == 'div' and tag.has_attr('id') and tag['id'] == 'toc':
        return True
    if tag.name == 'h1' and tag.has_attr('id') and tag['id'].lower() in toc_headings:
        return True
    if tag.name == 'h2' and tag.has_attr('id') and tag['id'].lower() in toc_headings:
        return True
    if tag.name == 'h1' and uGetTextSafe(tag).lower() in toc_headings:
        return True
    if tag.name == 'h2' and uGetTextSafe(tag).lower() in toc_headings:
        return True
    if tag.name == 'p': # N.B. paragraph is not a real option, but we need to count them
        return True
    
    return False

def TocFindHead(opts, bl, create_default):

    # this is the official wikipedia table of contents tool.

    par = 0
    for head in bl.find_all(TocCandidate):
        if head.name == 'p':
            par += 1
            if par > TOC_MAX_PAR:
                head = None
                break
        else:
            break

    if not head and create_default:
        # this is a sloppy way to find the head
        
        htmlroot = bl.find('div', class_='mw-content-ltr')
        assert htmlroot, 'Unable to find root of html text, mw-parser-output'
        html_1stitem = list(htmlroot.contents)[0]

        uPlogExtra(opts, 'TOC - placing before first tag "' + htmlroot.name +'" with body "' + \
                  uLabelDelWhite(uGetTextSafe(htmlroot)[0:50]), 2)

        head = bl.new_tag('div', class_='toc')  # make a fake head, so we can fined it later
        html_1stitem.insert_before(head)

        uPlogExtra(opts, "Inserting TOC as first tag before: " + html_1stitem.name + 
                  ' ' + uGetTextSafe(html_1stitem), 2)

        
    return head

def TocRemoveOldToc(opts, bl):
    """
    @summary: Find and remove any old Table of Contents listings in the document
    
    @note: This function destroys original content
    """

    mode = 0
    if not bl.find('div', class_='toc_wiki2epub'):
        # if we can't find our custom toc div, pick a location, and make one
        head = TocFindHead(opts, bl, True)
        assert(head), "Unable to find TOC location."
        toc = bl.new_tag('div')
        toc['class'] = 'toc_wiki2epub'
        head.insert_before(toc)
    else:
        # found our custom toc, pick a standard head
        head = TocFindHead(opts, bl, False)
    
    if not head:
        return 'Last TOC removed'
    
    if head.name == 'h1' or head.name == 'h2':
        mode = 1 

    uPlogExtra(opts, "=> Removing old TOC: " + head.name + ' ' +
              uLabelDelWhite(uGetTextSafe(head)[0:20]), 1)
    
    # Plow through until we reach a heading or some real text. Ignore any
    # empty paragraphs, or 
    #
    # This is risky, we don't really know exactly where we are in the tree,
    # but there do seem to be a lot of trashy TOC entries. Go for it!
    
    if mode == 1:
        
        curr = head.next_sibling
        tnext = head.next_sibling
        while tnext:
            curr = tnext
            if isinstance(curr, NavigableString):
                break

            tnext = curr.next_sibling

            if ( curr.name == 'h1' or
                 curr.name == 'h2' or
                 curr.name == 'h3' or
                 curr.name == 'p'):
                
                if curr.name == 'p':
                    curr_str = uGetTextSafe(curr)
                    if curr_str and len(curr_str) < 50:  # XXX stomps on homemad tocs 
                        break
                else:
                    break

            uPlogExtra(opts, "Toc - removing old entry: " + uGetTextSafe(curr)[0:20], 2)
            curr.decompose()
        
    head.decompose()   # had to write this

    return ''

def TocMake(opts, bl):

    toc = bl.find('div', class_='toc_wiki2epub')

    assert toc, "TOC tag not found. Should have been created by now."

    tag = bl.new_tag('h1', id='Contents_root')
    tag.string = 'Contents'
    tag['class'] = 'section'

    toc.append(tag)
    
    toc_list = bl.new_tag('ul')
    toc.append(toc_list)
    
    # Add our Contents label to the top of the list
    [hlist, hdlist] = TocGetH1H2([], [], tag, None)

    head = None
    for curr in bl.find_all(lambda x: x.name == 'h1' or x.name == 'h2'):
                [hlist, hdlist] = TocGetH1H2(hlist, hdlist, curr, head)

    TocMakeAndLinkTags(opts, bl, toc_list, hlist)

    # plus one accounts for the Contents entry
    toc_links = len(hlist) + 1

    uPlogExtra(opts, "=> Adding TOC with %d entries." % toc_links, 1)
    
    return toc_links
