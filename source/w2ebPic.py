"""
@summary:      W2EB - A tool for converting Wikipedia articles into ebooks.
@author:       Dave Gilbert
@contact:      dave.wm.gilbert@gmail.com
@license:      GPLv3
@requires:     Python 2.7, wget, Image Magick's convert, Beautiful Soup, Calibre
@since:        2019.04.10 
@version:      0.3
"""

import sys
from shutil import copyfile

from w2ebUtils import *
from w2ebConstPic import * 

# There are a few bad images that we see regularly... 
#
IMAGE_AVOID = ['Special:CentralAutoLogin']

TMP_DIR = '/tmp/'

def PicGetImage(opts, url, image_file):
    """
    Fetch image file from "url" save to output file name "image_file"
    """
            
    err = ''
    
    if opts['no_images']:
        return 1
    
    ind = url.find('://')
    fname = url[ind +3:]
#    fname = urllib.unquote(url[ind +3:])  # XXX these sometimes have unreadable characters in them

    image_dir = os.path.dirname(image_file)

    if os.path.exists(opts['dcdir'] + '/images/' + fname):
        #uPlog(opts, "cache hit found", opts['dcdir'] + '/images/' + fname

        opts['chits'] = opts['chits'] + 1
    else:
        log_file = '"' + opts['dcdir'] + '/images/wget_log.txt"'
        wgopts = WGET_OPTS + ' -o ' + log_file    
        wgopts = wgopts + ' --directory-prefix="' + opts['dcdir'] + '"/images '

        if opts['wikidown']:
            err = 'wikidown: -w disables wget fetches to wikipedia and relies on cached data'
            opts['wikidown'] += 1
        else:        

            err = uSysCmd(opts, '/usr/bin/wget ' + wgopts + ' "' + url + '"', 
                          opts['debug'])
            
            if not err:
                uPlogExtra(opts, "wget: " + url, 3)
                opts['wgets'] += 1
            else:
                uPlogExtra(opts, "Failed: wget " + url, 2)
                uPlogFile(opts, opts['dcdir'] + '/images/wget_log.txt', 2)

    if not err:
        uSysMkdir(opts, opts['bodir'] + '/' + image_dir)
        
        try:
            src_f = opts['dcdir'] + '/images/' + fname
            srcfile = urllib.unquote(src_f)
        ## urllib generates a noisy warning 
        
        #         with warnings.catch_warnings():
        #             warnings.simplefilter("ignore")
        #             srcfile = urllib.quote(src_f) # has some messy warnings. They don't seem important.
        
        #        srcfile = urllib.quote(src_f)
            copyfile(srcfile, opts['bodir'] + '/' + image_file)
        except Exception as e:
            uPlogFile(opts, opts['dcdir'] + '/images/wget_log.txt', 1)
            uPlogExtra(opts, "Exception: " + uCleanChars(str(e)), 1)
            err = 'Image name has messy control characters ' + uCleanChars(fname)
            # Sometimes wget garbles the dowloaded file name in a way that we can't guesss.
            # The right fix involves testing for messy strings prior to
            # download, and then specifying some safe version of the string later on...

    if not err and not os.path.exists(opts['bodir'] + '/' + image_file ):
        err = 'Missing file: ' + opts['bodir'] + '/' + image_file
    return err


def PicGetSvgDims(opts, str_line):
    """
    Read the dimensions of an SVG file
    
    @return: (retval - a string encoding <w>x<h>)
    """
    
    w = 0
    h = 0
    im_scale = 0
    
    # use the width tag to compute scaling, assume 
    # height tag agrees
    
    wstr = uSubstrBt(str_line, 'width="', 'ex"')
    if wstr:
        im_scale = IM_SCALEex
    
    if not wstr:
        wstr = uSubstrBt(str_line, 'width:', 'ex;')
        if wstr:
            im_scale = IM_SCALEex
    
    if not wstr:
        wstr = uSubstrBt(str_line, ' width="', '"')
        if wstr:
            im_scale = IM_SCALEpx
    
    if wstr:
        wi = int(float(wstr) * im_scale)
        if wi > WMAX:
            im_scale = WMAX / float(wstr)

    hstr = uSubstrBt(str_line, 'height="', 'ex"')
    if not hstr:
        hstr = uSubstrBt(str_line, 'height:', 'ex;')
    
    if not hstr:
        hstr = uSubstrBt(str_line, ' height="', '"')
        
    if hstr:
        hi = int(float(hstr) * im_scale)
        if hi > HMAX:
            im_scale = HMAX / float(hstr)

    if hstr and wstr:
        w = int(float(wstr) * im_scale)
        h = int(float(hstr) * im_scale)
    
    retval = str(w) + 'x' + str(h)
    
    if w * h == 0:
        assert 0, "Math Failed %f %dx%d %s" % (im_scale, h,w,str_line)
    if h < IM_SCALEex / 2:
        uPlogExtra(opts, "Small Math Dimensions %dx%d" % (h,w), 3)
        
    return retval

def PicFixPixelDims(bl, img_tag):
        
    if not img_tag.has_attr('width') or not img_tag.has_attr('height'):
        return
    
    wstr = img_tag['width']
    hstr = img_tag['height']

    # sometimes the image has lots of resolution but the 
    # page specifies it to be really small.
    
    # if the reported image width is >> MIN_IMAGE_W >> display  width
    # then adjust accordingly. 

    im_scale = IM_SCALEpx

    if int(wstr) * im_scale < MIN_IMAGEpxW:
        if img_tag.has_attr('data-file-width'):
            
            # If the original file is reported to be small
            # then scale it in the regulary way, it is likely an icon 
            #
            if float(img_tag['data-file-width']) * im_scale > MIN_IMAGEpxW:
                im_scale = MIN_IMAGEpxW / float(wstr)

    w = int(float(wstr) * im_scale)
    if w > WMAX:
        im_scale = WMAX / float(wstr)

    h = int(float(hstr) * im_scale)
    if h > HMAX:
        im_scale = HMAX / float(hstr)

    if im_scale > MAX_SCALEpx:
        im_scale = MAX_SCALEpx
    
            
    w = int(float(wstr) * im_scale)
    h = int(float(hstr) * im_scale)

    img_tag['width'] = str(w)
    img_tag['height'] = str(h)
    
    p1 = img_tag.parent
    p2 = p1.parent
    
    # The following code for cetering images is likely very brittle...
    
    if 'style' in p1.attrs:
        p1['style']='width:' + str(w) + 'px;'
    elif 'style' in p2.attrs:
        p2['style']='width:' + str(w) + 'px;'
        
        center_tag = bl.new_tag('center')
        p2.insert_before(center_tag)
        p2.extract()
        center_tag.append(p2)

png_bw = ' -colorspace Gray -depth 4 -colors 16 '
jpg_bw = ' -colorspace Gray '
resize = ' -resize "' + str(WMAX) + 'x' + str(HMAX) + '>" '
convcmd = 'convert -background "#FFFFFF" -flatten '

def PicConvertSVGcmd(opts, image_file, dosvg2png):
    
    fp_im = open(opts['bodir'] + '/' + image_file, 'r')
    l1 = fp_im.readline()
    fp_im.close()
    
    wxh = PicGetSvgDims(opts, l1)

    png_conv = convcmd
    if opts['bw_images']:
        png_conv = convcmd + png_bw
                                
    if l1[0:4] == "<svg":

        #
        # Wikipedia often provides .svg files that don't use the .svg extension,
        # I don't understand why. Create an explicit .svg link to the file to avoid
        # moving or copying it, but still get the right extension.
        #
        if not image_file[-4:] in IMAGE_SVG:
            if not os.path.exists(opts['bodir'] + '/' + image_file + '.svg'):
                err = os.symlink(opts['bodir'] + '/' + image_file, 
                           opts['bodir'] + '/' + image_file + '.svg')
        
        if not err and dosvg2png:
            if wxh:
                err = uSysCmd(opts, png_conv + '-resize ' + wxh + 
                        ' -quality 75 ' + '"' + opts['bodir'] + '/' + image_file + 
                        '.svg" ' + '"' + opts['bodir'] + '/' + image_file + '.png"', False)
            else:
                err = uSysCmd(opts, png_conv + resize + ' -quality 75 ' + opts['bodir'] + 
                          '/"' + image_file + '.svg" ' + opts['bodir'] + 
                          '/"' + image_file + '.png"', False)

    else:
        uPlogExtra(opts, 'Failed to convert "' + image_file, 2)
        uPlogExtra(opts, 'Expected "<svg " in header, found ' + l1[0:30], 2)
    
    return err

def PicConvertSVG(opts, image_file, image_url, convert, dosvg2png):

    err = ''
    # math .svg files never use the .svg extension. I don't know why.
    # Start by trimming the extension, should work for all cases
    if image_file[-4:] in IMAGE_SVG:
        image_file = image_file[:-4]

    if (dosvg2png and
        os.path.isfile(opts['bodir'] + '/' + image_file + '.png')):
            image_file = image_file + '.png'
            uPlogNr(opts, "p")
            opts['chits'] = opts['chits'] + 1
    elif (not dosvg2png and
        os.path.isfile(opts['bodir'] + '/' + image_file + '.svg')):
            image_file = image_file + '.svg'
            uPlogNr(opts, "s")
            opts['chits'] = opts['chits'] + 1
    else:
        err = PicGetImage(opts, image_url, image_file)
        if not err:
            err = PicConvertSVGcmd(opts, image_file, dosvg2png)
        if not err:
            convert = convert + 1
            if dosvg2png:
                uPlogNr(opts, "P")
                image_file = image_file + '.png'
            else:
                image_file = image_file + '.svg'
                uPlogNr(opts, "S")
    if err:
        err = "Unable to convert math image, " + err
                
    return err, image_file, convert

def PicConvertImage(opts, image_url, image_file, suff):
    
    
    # sometimes we fail to get the file. The most common reason
    # is complicated escape sequences. XXX should fix

    png_conv = convcmd
    jpg_conv = convcmd
    
    if opts['bw_images']:
        png_conv = convcmd + png_bw
        jpg_conv = convcmd + jpg_bw

    pid = str(os.getpid())

    if suff in IMAGE_FIG:
        err = uSysCmd(opts, png_conv + '-resize ' + IM_SCALEperc + resize + 
                      '-quality 75 ' + '"' + opts['bodir'] + '/' + image_file +
                      '" ' +TMP_DIR + '/conv_' + pid + '.png', False)
        if not err:
            uSysMkdir(opts, os.path.dirname(opts['bodir'] + '/' + image_file))
            err = uSysCmd(opts, 'mv ' + TMP_DIR + '/conv_' + pid + '.png "' +
                          opts['bodir'] + '/' + image_file + '"', False)

    elif suff in IMAGE_PIC:
        err = uSysCmd(opts, jpg_conv + '-resize ' + IM_SCALEperc + resize +
                      '-quality 75 ' + '"' + opts['bodir'] + '/' + image_file +
                      '" ' + TMP_DIR + '/conv_' + 'pid' + '.jpg', False)
        if not err:
            uSysMkdir(opts, os.path.dirname(opts['bodir'] + '/' + image_file)) # XXX may be unnecessary...
            err = uSysCmd(opts, 'mv ' + TMP_DIR + '/conv_' + pid + '.jpg "' +
                          opts['bodir'] + '/' + image_file + '"', False)

    if not err:
        suff = PicImType(suff)

    return err, suff


def PicIdentifyImageType(image_url, image_file, opts):
    """
    Use the unix file command to identify images
    
    @return link the file to a renamed version with a meaningful .<ext>
    """

    # unrecognized file type

    src = opts['bodir'] + '/' + image_file
                    
    if not os.path.isfile(src):
        PicGetImage(opts, image_url, image_file)

    ext = uSysCmdOut1(opts, 'file "' + src + '"', True)
    ext = uSubstrBt(ext,': ',' ')

    if ext in IMAGE_FIG + IMAGE_PIC + IMAGE_SVG:
    
        # if image_file had an unrecognized extension conver it
        # to one we are more likely to recognize
    
        if src[-len(ext):] != ext:
            dst = opts['bodir'] + '/' + image_file + '.' + ext
            
            if not os.path.exists(dst):
                os.symlink(src, dst)
    
            image_file = image_file + '.' + ext
    else:
        image_file = ''

    return image_file

def PicGetUrlFileName(opts, img_tag):
    """
    extract from the tag the image url, and a file name to save it to
    """

    # default image url
    image_url = img_tag['src'] 
    alt_image = ''
    # wikipedia seems to have 3 versions of files.
    # usually srcset x2 image is the largest. 
#     ptag = img_tag.parent
# 
#     if ptag.name == 'a':
#         if ptag.has_attr('href'):
#             image_url = img_tag.parent['href']
#             # now what about image dimensions?
    image_file = ''

    if img_tag.has_attr('srcset'):
        alt_image = uSubstrBt(img_tag['srcset'], '1.5x, ', ' 2x')
        if (alt_image):
            image_url = alt_image 

    # XXX not 100% sure that alt images will always have https prefix
    prefix = '//'
    if image_url[0:len(prefix)] == prefix:
        image_url = 'https://' + image_url[2:]

    prefix = '/static/images/'
    if image_url[0:len(prefix)] == prefix:
        image_url = 'https://wikipedia.org' + image_url

            
    for prefix in ['https://', 'http://']:
        if image_url[:len(prefix)] == prefix:
            image_file = image_url.replace(prefix, 'images/')
            image_file = urllib.unquote(image_file)  # XXX do this here or in PicGetImage, not both
            #image_file = uCleanChars(opts, urllib.unquote(image_file))   # XXX some files use odd characters 
    
    if alt_image:
        uPlogExtra(opts, "Using alt_image: " + image_url, 3)
    else:
        uPlogExtra(opts, "Using default image: " + image_url, 3) 
    
    # image_file has to go through several shell commands, must be plaintext
    #
    assert image_file, "Image_URL = " + image_url
    
    # image_file = urllib.quote(image_file)  # XXX is this necessary??? Creates problems, Mona Lisa for example
    
    return [image_url, image_file]

def estimate_runtime(bl):

    im_all = 0
    im_math = 0
    
    for img_tag in bl.find_all('img', src=True):

        im_all = im_all + 1
            
        if '/math/render/svg/' in img_tag['src']:
            im_math = im_math + 1
        
    p_total_est_time = im_math * 2 + im_all
    
    return [p_total_est_time, im_all, im_math]
    


def PicImType(suff):
    
    if suff[0] == '.':
        return suff[1]
    return suff[0]
    
def PicGetImages(opts, bl):

    im_tot = 0
    convert = 0           
    [p_total_est_time, im_all, im_math] = estimate_runtime(bl)
 
    st_time = time.time()
    ostr = '\nCollecting Figures (J/P)'
    if im_math:
        ostr += ', and Renderning Math Equations (M)'
    uPlog(opts, ostr) 
    uPlogExtra(opts,'',1) # Log needs an extra space here
 
    for img_tag in bl.find_all('img', src=True):
        
        err = ''
        if im_tot % 25 == 0:
            p_total_est_time = uPrintProgress(opts, st_time, im_tot, im_all,
                                              p_total_est_time)
        sys.stdout.flush()
        
        [image_url, image_file] = PicGetUrlFileName(opts, img_tag)

        cont = False
        for bad_image in IMAGE_AVOID:
            if bad_image in image_url:
                cont = True
                
        if cont:
            img_tag['src'] = ''      # XXX can we do this, lets try
            uPlogExtra(opts, "Filtering " + image_url, 2)
            continue

        img_tag['src'] = opts['bodir'] + '/' + image_file

        suff = image_file[-4:]

        if suff not in IMAGE_FIG + IMAGE_PIC + IMAGE_SVG and not '/math/render/svg/' in image_file:
            
            image_file = PicIdentifyImageType(image_url, image_file, opts)
            suff = image_file[-4:]
        
        if suff in IMAGE_FIG + IMAGE_PIC:
            PicFixPixelDims(bl, img_tag)
            
            if not os.path.isfile(opts['bodir'] + '/' + image_file):
                err = PicGetImage(opts, image_url, image_file)
                if not err:
                    err, image_type = PicConvertImage(opts, image_url, image_file, suff)
                if not err:
                    convert = convert + 1
                    uPlogNr(opts, image_type.upper())
                    img_tag['src'] = opts['bodir'] + '/' + image_file

            else:
                opts['chits'] = opts['chits'] + 1
                uPlogNr(opts, PicImType(suff).lower())

        elif '/math/render/svg/' in image_file:

            err, image_file, convert = PicConvertSVG(opts, image_file, image_url,
                                                     convert, opts['svg2png'])
            if not err:
                img_tag['src'] = opts['bodir'] + '/' + image_file

        elif suff in IMAGE_SVG:

            err, image_file, convert = PicConvertSVG(opts, image_file, image_url,
                                         convert, opts['svg2png'] or not opts['svgfigs'])
            if not err:
                img_tag['src'] = opts['bodir'] + '/' + image_file

        else:                
            uPlogNr(opts, "-")
            uPlogExtra(opts, "XXX unknown file type: " + image_url, 1)
            img_tag['src'] = ''      # XXX can we do this, lets try

        if err:
            uPlogNr(opts, "x")
            uPlogExtra(opts, "Unable to get image (x), " + err, 2)
            img_tag['src'] = ''      # XXX can we do this, lets try
        else:
            
            assert os.path.exists(opts['bodir'] + '/' + image_file), "Missing image\n" +\
                "Url = " + image_url + '/' + "\nFile = " + opts['bodir'] + '/' + image_file
        im_tot = im_tot + 1
        
    uPlogNr(opts, '\n')

    return im_tot, convert
