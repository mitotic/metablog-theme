#!/usr/bin/env python3
# Process Hugo Markdown blog posts to create book using Pandoc
# https://learnbyexample.github.io/customizing-pandoc/

# Example:
#   blog2book.py --url=https://example.com --posts-dir=content/posts --output-dir=public/ebook --output=book.epub --title=MyBlog --author="My Name" --css=pandoc/book.css --last-date-file=lastdate.txt --recent=3 pandoc/title.txt content/page/about.md content/page/links.md

import sys, os, yaml, datetime, subprocess, tempfile, argparse
from pathlib import Path

def expand_date(d):
    return d[:4]+'-'+d[4:6]+'-'+d[6:] if d else ''

def blog2book(posts_dir, output_dir, output_file, site_url, site_title, site_author, twitter_handle, remarks_json_gzfile, css_file, cover_image, last_date_file, force, hidden, individual, recent, filenames):
    # Creates modifed copies of markdown files (filenames) in temporary directory
    # making minor changes to Hugo markdown to work with Pandoc by extracting title etc.
    # If output_file has extension .epub or .pdf, only files of that type are created. Otherwise both types are created.
    # If last_date_file is specified, add suffix YYYYMMDD to output_file (before extension)
    # If recent > 0, only output recent files
    # returns last post date (YYYYMMDD) as string

    title_name = 'title.txt'
    extensions = ('.epub', '.pdf')
    
    outdir = Path.cwd() / Path(output_dir) if output_dir else Path.cwd()
    outpath = outdir / output_file

    if outpath.suffix in extensions:
        suffixes = [ outpath.suffix ]
    else:
        suffixes = extensions[:]

    remarks_dict = {}
    if remarks_json_gzfile:
        remarks_dict = read_remarks(remarks_json_gzfile)

    filenames = filenames[:]
    if posts_dir:
        if not os.path.isdir(posts_dir):
            raise Exception(posts_dir+ ' not found')
        for fname in os.listdir(posts_dir):
            fpath = posts_dir + '/' + fname
            filenames.append(fpath)

    sections = []
    unnumbered_count = 0
    prev_last_date = ''
    if last_date_file and os.path.isfile(last_date_file):
        with open(last_date_file) as f:
            prev_last_date = f.read().strip()

    last_date_val = ''
    title_path = None
    with tempfile.TemporaryDirectory() as tmpdirname:
        imgdir = tmpdirname + '/image'
        os.mkdir(imgdir)

        for filename in filenames:
            inname = filename
            fpath = Path(Path.cwd() / filename)

            if fpath.name.startswith('.') or fpath.name.startswith('_'):
                # Skip .* files
                continue

            if fpath.name == title_name:
                # Frontmatter for epub (YAML)
                title_path = fpath
                continue

            if os.path.isdir(fpath):
                index_file = filename + '/index.md'
                if not os.path.isfile(index_file):
                    raise Exception(index_file + ' not found')
                outname = fpath.name + '.md'
                inname = index_file
                postimgdir = str(fpath/'image')
                if os.path.isdir(postimgdir):
                    for imgfile in os.listdir(postimgdir):
                        if imgfile.startswith('.'):
                            continue
                        # Symlink images to directory
                        destname = imgdir+'/'+imgfile
                        if os.path.exists(destname):
                            raise Exception('Duplicate image name '+imgfile)
                        os.symlink(postimgdir+'/'+imgfile, destname)
            else:
                outname = fpath.name

            link_path = '/' + fpath.parent.name + '/' + fpath.stem
            link_url = site_url + link_path

            with open(inname, "r") as f:
                lines = f.readlines()
            frontmatter = None
            textlines = None
            for line in lines:
                if frontmatter is None:
                    if line.lstrip().startswith('---'):
                        frontmatter = []
                    else:
                        continue
                else:
                    if textlines is None:
                        if line.lstrip().startswith('---'):
                            textlines = []
                        else:
                            frontmatter.append(line)
                    else:
                        textlines.append(line)

            if frontmatter:
                preface = ''.join(frontmatter)
                data = yaml.load(preface, Loader=yaml.FullLoader)
            else:
                preface = ''
                data = {}

            textlines = textlines or []

            if not hidden and (data.get('draft') or data.get('Draft') and data.get('unlisted') or data.get('Unlisted')):
                continue

            title = data.get('title') or data.get('Title') or ''
            pubdate = data.get('date') or data.get('Date') or ''
            thumbnail = data.get('thumbnail') or data.get('Thumbnail') or ''
            card = data.get('card') or data.get('Card') or ''
            tweetid = data.get('tweetid') or data.get('Tweetid') or ''
            pubdate = str(pubdate).replace('-','')

            tweet_url = ''
            if twitter_handle and tweetid:
                tweet_url = 'https://twitter.com/'+twitter_handle+'/status/'+str(tweetid)

            author = data.get('author') or data.get('Author') or site_author

            unnumbered = not pubdate or data.get('unnumbered') or data.get('Unnumbered')

            ntitle = title
            if unnumbered:
                pubdate = ''
                ntitle = ntitle + ' {.unnumbered}'
                unnumbered_count += 1

            feature = card or thumbnail
            if feature:
                feature = str(fpath / ('image/' + Path(feature).name))

            sections.append( (pubdate, outname, title, author, feature) )

            if thumbnail:
                textlines = ['![](image/' + Path(thumbnail).name + ')\n\n'] + textlines

            if pubdate:
                byline = site_title+' '+expand_date(pubdate)
                textlines = ['\n\n['+byline+']('+link_url+')\n\n'] + textlines

            description = data.get('description') or data.get('Description')
            if description:
                textlines = ['*' + description + '*\n\n'] + textlines

            textlines = ['# ' + ntitle + '\n\n'] + textlines

            if not unnumbered:
                textlines += [ '\n\n## Comments\n\n*Note:* For updated comments, see the [original blog post]('+link_url+'/)'+(' and the [anouncement tweet]('+tweet_url+')' if tweet_url else '')+'.\n\n' ]
                post_comments = remarks_dict.get(link_url+'/')
                if post_comments:
                    textlines += [ '\n\n'+post_comments ]

            textlines += [ '\n\n---\n' ]

            with open(Path(tmpdirname) / outname, 'w') as f:
                f.write(''.join(textlines))

        if not sections:
            raise Exception('No files to process')

        sections.sort()
        last_date_val = sections[-1][0]
        last_feature = sections[-1][-1]

        if last_date_file:
            with open(last_date_file, 'w') as f:
                f.write(last_date_val)

        css_path = str(Path.cwd() / css_file)
        pdf_options = [ '-V', 'colorlinks', '-V', 'geometry:margin=1.2in', '-V', 'mainfont=DejaVu Serif', '-V', 'monofont=DejaVu Sans Mono', '--pdf-engine=xelatex' ]

        if individual:
            count = 0
            for pdate, fname, title, author, feature in sections:
                if not pdate:
                    continue
                count += 1

                pandoc_cmd = ['pandoc', '-s', '-M', 'title='+title, '-M', 'rights='+author, '--css='+css_path, '--number-offset='+str(count-1)]
                if cover_image:
                    imgpath = 'image/'+pdate+'-cover.png'
                    annotate_image(cover_image, tmpdirname+'/'+imgpath, text=title, feature_image=feature, top_margin=0.075, bot_margin=0.25)
                    pandoc_cmd += [ '--epub-cover-image='+imgpath ]

                for extn in suffixes:
                    indpath = outdir / (pdate + '-' + Path(fname).stem + extn)

                    if os.path.isfile(indpath) and pdate <= prev_last_date and not force:
                        continue

                    pandoc_cmd2 = pandoc_cmd[:]
                    
                    if extn == '.pdf':
                        pandoc_cmd2 += ['-M', 'author='+site_title+'/'+author] + pdf_options
                    else:
                        pandoc_cmd2 += ['-M', 'author='+site_title]

                    pandoc_cmd2 += ['-o', str(indpath) ]
                    pandoc_cmd2 += [ fname ]

                    ##print(pandoc_cmd, file=sys.stderr)
                    create_book = subprocess.run(pandoc_cmd2, text=True, cwd=tmpdirname)
                    print('Created', indpath.name, file=sys.stderr)

        if not output_file or len(sections) < 2:
            # No combined output file
            return last_date_val

        if recent:
            cover_text = 'Recent posts ' + expand_date(last_date_val)
        else:
            cover_text = 'All posts ' + expand_date(last_date_val)

        if title_path:
            with open(title_path, "r") as f:
                text = f.read()

            text = text.replace('TITLE', site_title+' '+cover_text)
            text = text.replace('AUTHOR', site_author)
            text = text.replace('DATE', expand_date(last_date_val) if last_date_file else str(datetime.date.today()) )

            with open(tmpdirname+'/'+title_path.name, 'w') as f:
                f.write(text)

        pandoc_cmd = ['pandoc', '-s', '--css='+str(Path.cwd() / css_file), '--toc' ]

        if recent and len(sections) > unnumbered_count + recent:
            # Retain only most recent posts
            number_offset = len(sections) - recent - unnumbered_count
            mdfiles = [fname for (pdate, fname, title, author, feature) in sections[-recent:]]
            pandoc_cmd += [ '--toc-depth=2', '--number-offset='+str(number_offset) ]
        else:
            # All posts
            number_offset = 0
            mdfiles = [fname for (pdate, fname, title, author, feature) in sections]
            pandoc_cmd += [ '--toc-depth=1', '--number-offset=0' ]

        if cover_image:
            imgpath = 'image/CoverImage.png'
            annotate_image(cover_image, tmpdirname+'/'+imgpath, text=cover_text, feature_image=last_feature, top_margin=0.075, bot_margin=0.25)
            pandoc_cmd += [ '--epub-cover-image='+imgpath ]

        outprefix = str( Path(outpath.parent / outpath.stem) )
        if last_date_file:
            outprefix += '-' + last_date_val
        
        for extn in suffixes:
            outfile = outprefix + extn

            if not force and os.path.isfile(outfile) and last_date_val >= prev_last_date:
                continue

            pandoc_cmd2 = pandoc_cmd[:]
            if extn == '.pdf':
                pandoc_cmd2 += pdf_options + ['-M', 'title='+site_title+' '+cover_text]
            elif title_path:
                pandoc_cmd2 += [title_name]

            pandoc_cmd2 += ['-o', outfile ] + mdfiles

            ##print(pandoc_cmd2, file=sys.stderr)

            create_book = subprocess.run(pandoc_cmd2, text=True, cwd=tmpdirname)

            ##print(create_book, file=sys.stderr)
            print('Created', outfile, file=sys.stderr)

        return last_date_val

def annotate_image(cover_image, out_image, text='', feature_image=None, top_margin=0.1, bot_margin=0.1, fontname='DejaVuSans', fontdir='', fontsize=72, text_width=16, text_color='#000000'):
    # Example: annotate_image('cover.png', 'newcover.png', text='The quick brown fox', feature_image='feature.png', top_margin=0.075, bot_margin=0.25)
    from PIL import Image, ImageDraw, ImageFont
    import site, textwrap

    cover = Image.open(cover_image)
    draw  = ImageDraw.Draw(cover)
    page_wid, page_ht = cover.size

    if not fontdir:
        fontdir = site.getsitepackages()[0] + '/matplotlib/mpl-data/fonts/ttf'
    font = ImageFont.truetype(fontdir+'/'+fontname+'.ttf', fontsize, encoding='unic')
    lines = '\n'.join(textwrap.wrap(text, width=text_width))
    txwid, txht = font.getsize_multiline(lines)

    txfrac = txht / page_ht

    img_tmargin = 0.05
    img_lmargin = 0.1

    # Fractional available height
    avail_frac = 1.0 - (txfrac + top_margin + img_tmargin + bot_margin)

    if feature_image and avail_frac > 0:
        try:
            image2 = Image.open(feature_image)
            img2_wid, img2_ht = image2.size

            # Fractional height occupied by feature image
            img2_frac = (((1-2*img_lmargin)*page_wid/img2_wid) * img2_ht) / page_ht

            if img2_frac > avail_frac:
                # Shrink feature image
                img2_frac = avail_frac

            img2_ht2 = int(img2_frac * page_ht)
            img2_wid2 = int(img2_ht2*(img2_wid/img2_ht))

            image2 = image2.resize( (img2_wid2, img2_ht2) )

            xoffset = int(0.5*(page_wid -img2_wid2))
            yoffset = int( (top_margin + txfrac + img_tmargin + 0.5*(avail_frac - img2_frac))*page_ht )

            cover.paste(image2, (xoffset,yoffset) )
        except Exception as inst:
            print('annotate_image:', inst, file=sys.stderr)

    draw.multiline_text( (int(0.5*(page_wid-txwid)), int(top_margin*page_ht)), lines, fill=text_color, font=font)

    cover.save(out_image,'PNG')


def read_remarks(remarks_json_file):
    # Read Remark42 comments from JSON file and return dict of comment HTML
    # with post URL as key
    import gzip, json, re
    from collections import defaultdict

    list_markers = '-+*'

    def process_comment_list(comment_list, level=0):
        # Comment tree structure
        # [ (time, id), ..., ]
        comment_list.sort()
        retval = []
        for _, comment_id in comment_list:
            retval += process_comment(comment_id, level)
        return retval

    def process_comment(comment_id, level):
        comment = all_comments[comment_id]
        lmax = min(level, 2)
        retval = [ '  '*lmax+list_markers[lmax]+' *' + comment['user']['name'] + '*: ' + re.sub('\n+', '\n', comment['text']) ]
        return retval + process_comment_list(comment['subcomments'], level+1)

    with gzip.open(remarks_json_file, 'r') as f:
        lines = f.readlines()
        comment_list = [json.loads(line) for line in lines[1:]]

        all_comments = {}
        post_comments = defaultdict(list)

    for comment in comment_list:
        if comment.get('delete'):
            continue
        comment['subcomments'] = []
        all_comments[comment['id']] = comment
        if comment['pid']:
            all_comments[comment['pid']]['subcomments'].append( (comment['time'], comment['id']) )
        else:
            post_comments[comment['locator']['url']].append( (comment['time'], comment['id']) )

    post_processed_comments = {}
    for post_url, post_comment_list in post_comments.items():
        post_processed_comments[post_url] = '\n'.join(process_comment_list(post_comment_list)) + '\n\n'

    return post_processed_comments

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', type=str, required=True, help='site url')
    parser.add_argument('--title', type=str, required=True, help='site title')
    parser.add_argument('--author', type=str, required=True, help='site author')
    parser.add_argument('--posts-dir', type=str, help='posts directory, e.g., content/posts')
    parser.add_argument('--output-dir', type=str, help='output directory')
    parser.add_argument('--output', type=str, help='Name of combined output file')
    parser.add_argument('--twitter', type=str, help='Twitter handle')
    parser.add_argument('--remarks', type=str, help='Name of Remarks42 comments JSON .gz file')
    parser.add_argument('--css', type=str, required=True, help='CSS file path')
    parser.add_argument('--cover_image', type=str, help='Annotatable cover image file')
    parser.add_argument('--last-date-file', type=str, help='read/save last date and append to combined file name')
    parser.add_argument('--force', action='store_true', help='Force creation of files, even if present and up-to-date')
    parser.add_argument('--hidden', action='store_true', help='Handle hidden (draft/unlisted) files')
    parser.add_argument('--individual', action='store_true', help='Create individual files for each post')
    parser.add_argument('--recent', type=int, help='Create combined file of recent posts')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()

    last_date_suffix = blog2book(args.posts_dir, args.output_dir, args.output, args.url, args.title, args.author, args.twitter, args.remarks, args.css, args.cover_image, args.last_date_file, args.force, args.hidden, args.individual, args.recent, args.files)

    if args.last_date_file:
        print(last_date_suffix)
