# w2eb

**w2eb** Converts Wikipedia pages to ebooks.

Why would you want this? 

E-ink readers are fantastic devices but have a large number of limitations in terms of what they can render. A basic e-reader has a 600x800 monochrome pixel display, small memory storage, and performs poorly when used as a web browser.

Wikipedia's database is a great source for content. While you can convert web pages with Amazon's "send to kindle" web browser plug-in, "send to kindle" is a generic answer not really tuned to Wikipedia's content.

# w2eb Features

**w2eb** takes a topic name and converts it into a wikipedia derived "ebook". It supports the following features:

1. Follows "Primary" links to create subsections
  * **w2eb** is selective about which links it explores completely.
  * **w2eb** provides simple controls to help you define what to include.
2. **w2eb** Summarizes "Secondary" links to create notes and footnotes.
  * Wikipedia articles often include hundreds of references, **w2eb** presents these as footnotes
  * A **w2eb** footnote is the first few sentences of a referred Wikipedia article.
  * Footnotes can be disabled and presented as internet links to reduce file sizes.
  * Footnoes can be extended with Notes. **w2eb** preserves the first 10 paragraphs of any wikipedia reference and the original in a special Notes section.
3. **w2eb** Organizes related wikipedia links into a "book"
  * **w2eb** Arranges the pages it downloads in a breadth first pattern, so that if you read your wikibook start to finish it will make a certain sense.
  * **w2eb** Stores all footnotes at the end of the book, alphabetizing them, and storing extended notes in a final section.
4. **w2eb** simplifies pages while preserving as much content as it can.
  * Wikipedia pages follow a consistent format but include formatting details that ereaders cannot display. Rather than completely reconstructing the page **w2eb** removes the elements it knows an ereader cannot render.
5. **w2eb** is image friendly.
  * Wikipedia usually stores several versions of each image. **w2eb** finds the "best" one for your reader and fetches it. The "best" image is about 600x600 pixels. This size leaves some space at the top or bottom for a caption. 
6. **w2eb** is math friendly.
  * Wikipedia stores math equations in .svg format. If your reader supports this format, great! If your reader doesn't support it, **w2eb** will convert the file for you.

# Why this tool?

It is easy to find fiction in epub format. Project Gutenburg and Archive.org sources for free books, and if you want the latest publications you can go to Amazon or your local library. Despite all these many good sources of fiction in epub format, it is very hard to find scientific or mathematically based content formatted for an ereader. Project Gutenberg hosts only a small selection of math and science books and these are in pdf and Latex format, not epub or html format.

Other web sites that provide science based media limit their offerings to pdf files. See for example the Openstax collection of University freshman level text books. You can get a Kindle version of their astronomy text book for free through the Amazon store, but not the Physics, Calculus, or Statistics books. These books are only offered in pdf format. While the tool they use will generate epub files, they don't post epub files because of lack of interest and the cost associated with maintaining additional formats. This is what one representative told me at least.

It is very difficult to properly convert a pdf file to an epub file. The most interesting tool for this job is k2pdfopt, which effectively treats each page of the pdf file as an image, cuts the image up, and then rearranges it so that it makes sense on the smaller geometery of an ereader's display. The k2pdfopt tool is a great, but it requires some tinkering to get the settings correct for each .pdf file, and once a file is converted fonts cannot be resized. 

Some people say- get a bigger tablet, and yes this is an answer. A tablet with a sufficiently high resolution and enough CPU cycles will allow you to read whatever electronic file you want on a portable table. For me, the whole appeal of the eink reader is that it is inexpensive, small, highly portable, and with cloud support provided by Amazon losing it isn't a big deal.

Nothing beats an e-ink display for readability and battery life. With amazon's cross platform support you can also read the same book on a phone that you have on your e-reader. My phone is really small, I like it that way for the sake of portability, but that means that if I want to read on it I need the font to be resizable and I appreciate it when the other limitations of small devices are respected.

# Demo

In the demo directory there are a few sample epub books generated by **w2eb**.

# Dependencies

The current version of **w2eb** has several dependencies. HTML files are fetched by *wget* and processed by *Beautiful Soup*, both must be present for the tool to work. Images are processed by *Image Magick's* *"convert"* command line tool. Testing has only been done on Linux. **w2eb** generates .html files that are epub friendly, but still relies on third party tools to do the final conversion. **w2eb** adds some tags that help *calibre* recognize headings that should be included in the table of contents.

# Usage

**w2eb** is written for Python 2.7. While it is a command line tool with a variety of options, it is meant to be simple to use. Suppose you want the Wikipedia book on Aardvarks, you would type:

`gilbert@dave:~$ wiki2epub.sh -b aardvark`

The speed of the tool is mainly limited by the speed of your Internet connection. Because of the size of Wikipedia book downloads are limited by the '-d' flag. This determines the "depth" of a search. The default setting for this flag is 1, which means that the tool will collect some of the subsections mentioned on the first page, but no subsections mentioned by child pages. **w2eb** generates several progress meters with summary symbols so you have an idea of what it is doing. Downloading the "aardvark" book generates the following output:

```
gilbert@dave:~$ wiki2epub.sh -b aardvark


---------------------------------------------
==> Downloading Wikibook "aardvark"
Started at Tue Jul 16 14:57:31 2019
Searching: https://en.wikipedia.org/wiki/aardvark
Debug = 1, Depth = 1

Fixing Tags: id sc li me sp ti jl np na ta di td ft pf cl hi hi gn 

Collecting Figures (J/P)

 0 %  16 secs left > P J P P P J J J J J J J J P P P 

Collecting Footnotes (F), Articles (A), and Internet Links (I)

 0 % 112 secs left > * / F F F F F F F F F F F F F F F F F * F F F F F 
 7 %   3 mins left > F F F F F F F F F F f F F F F F F F F f F f f f F 
14 % 154 secs left > F F F F F F F F F F F F f F F f * F F f * F F F F 
22 % 136 secs left > F F F F F F F F F F F F F F F F F F F F F F F F F 
29 % 158 secs left > F F F F F F F F F F F F F F F F F F F F F F F F F 
36 % 159 secs left > F f f F F F F F F F F F f f f F F F F F * * F F F 
44 % 149 secs left > F F F F F F F F F F F F F F F F F F F F F F F F F 
51 % 134 secs left > F F F F F F F I i * F I F * F * F I I f I f * f I 
59 % 115 secs left > I F I I I * I I I I f I f I F / f / I F F f / I f 
66 %  93 secs left > / I I f I I F I f / F I f / f I I f / f / * I I I 
73 %  74 secs left > * I F I I F I I I F / F I f f f F F F F F F F F F 
81 %  57 secs left > F F F F F F F F F F F F F F f F F F F F F F F F F 
88 %  35 secs left > F F F F F F F F F F F I F I F I F I F I F I F I F 
96 %  12 secs left > I F I F I F I f I F I F I 
=================Finalizing==================

Found 16 Figures, Converted 16 Figures
Extracted 232 Footnotes.
Internet Refs = 283, Page Refs = 1258, Bad Links Removed = 10, http 404 = 11
Internet Accesses = 554, Cache hits = 79
Table of Contents Entries = 16

Finished at Tue Jul 16 15:02:38 2019
Conversion took   5 mins

wrote aardvark/aardvark.html
==> Done
```

## Performance

**w2eb** maintains a cache of everything it downloads. This is mainly for development since downloading individual files consumes a large amount of time. After a book is created the first time, recreating it a second time with different settings is much faster. Cache erasure is controled by '-c', '-C', and '-K'. Each flag erases successively more of the cache with '-K' erasing everything.

A typical article can be downloaded and processed in about 5 minutes, although execution time depends more on the sort of internet connection you have and what article you are downloading.

Converting .svg files into .png files can be very time consuming, especially for books which define a large number of equations. For the kindle e-reader, .svg files with transparent background are rendered as black, so by default an .svg image which does not appear to be a math equation is converted to a .png file. In my tests I did not see any equation files that used transparent backgrounds so by default these are not converted. 

All footnotes and sections are merged into a single file which requires **w2eb** to harmonize all of the cross referenced links. This can take a while if the ebook being generated is very large. 

## Usage details

**w2eb** provides a detailed usage message.

```
gilbert@dave:~$ w2eb -h

w2eb.py, A script for converting Wikipedia articles into ebooks.

    Usage:  w2eb.py  [opts] [-u <URL>] [-b <book>] 
        
        -c        Erase .html files and retry URLs that previously failed.
        -C        Erase generated files: .html, images, and footnotes.
        -K        Erase all generated files and all cached downloads.
                    Without c, C, or K, a run will rewrite root doc only.
        -E        Export book to epub. Uses calibre for conversion.
        
        -n        No images 
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
        -S <typ>  Section type. Determines whether a link is treated
                    as a subsection or not.
                    
                    <typ> can be one of:
                    bookurl  - subsection url has book url as a substring
                    bookname - subsection url has book name as a substring
                               < default>
                    bookword - subsection url has at least one 4 letter word
                            from book name as substring
        
        -D <#>    Debug level. 0 = none, 1 = footnote only, 2 = failure only,
                    3 = all. Debug notes are included in the book by default.
        -w        Wiki down, rely on cache instead of wget (debugging...)
        -h        This message.
```

# Contact

Questions or comments are welcome.

dave.wm.gilbert@gmail.com
