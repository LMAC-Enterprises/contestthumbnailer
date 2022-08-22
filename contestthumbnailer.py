import argparse
import datetime
import io
import os
import platform
import re

import beem
import requests
import tempfile

from beem.comment import Comment
from PIL import Image, ImageDraw, ImageFont

"""
    Creates a thumbnail grid markup/markdown of all collage contest entries from the comments of a specific contest announcement post.
    
    Requirements:
    - https://github.com/holgern/beem (pip3 install -U beem)
    - Python 3.x
    
    Example (Creating an HTML file):
    python3 contestthumbnailer.py -html 1 -a "@shaka/lets-make-a-collage-a-contest-for-all-creatives-on-hive-round-107-182-hive-in-the-prize-pool"
    
    Example (Creating a markdown file):
    python3 contestthumbnailer.py -a "@shaka/lets-make-a-collage-a-contest-for-all-creatives-on-hive-round-107-182-hive-in-the-prize-pool"

    :author:    QuantumG
    :date:      01/14/2022
"""

REGEX_IMAGE_URL = r'((?:https://.*\.(?:gif|jpg|png|jpeg))|(?:https://images\.hive\.blog/p/[A-Za-z0-9_\-@\/]*)|(?:https://images\.ecency\.com/p/[A-Za-z0-9_\-@\/]*))'
REGEX_POST_URL = r'(https://(?:peakd\.com|hive\.blog|ecency\.com)/[a-z0-9_\-@\/\.]*)'

DEFAULT_IMAGE_URL = 'https://files.peakd.com/file/peakd-hive/quantumg/23tSh9ZCk2m46Yy9XQeQErkwL99fsdQjsxH9A6T4WKyi7BCDs3y4Q6pE3zMfDF4ggv5TS.png'

MAX_THUMBNAIL_WIDTH_IN_IMAGE = 160
THUMBNAIL_MARGIN_IN_IMAGE = 10
MAX_THUMBNAILS_PER_ROW_IN_IMAGE = 20
THUMBNAIL_LABEL_COLOR = (255, 255, 255)
THUMBNAIL_POSTER_COLOR = (0, 0, 0, 0)
IGNORE_DEFAULT_IMAGES_IN_POSTER = True

AUTHOR_BLACKLIST = ["abdt","abiproud","adebayo22","airscam00","aliframadhan","aniascs","anne0208","aris-indonesia","artrage","assegai","ayahdindin","belovedave","boeh-u-leuping","bulukat2seung","camila-jhon","captain70","chipino","daniella619","danladi","deep.crypto","dreamchasers","dwixer","ellenklech","emerline","ferart01","fibre1","filipz","findoutmark","fudin-jfr","fundin-jfr","gabriella3594","getovertools","ghinamidrara","giftjames","gomessteem","hafis","hardiericsson","herman-sbd","holy.moly","iamdenny","icon-bassey","jhokenecty","kadyrova","kalkulus001","kamariah","kater001","khantika","kingobonnaya","lamboe","lexi01","lilpen","loco88","mawalampoehbujok","mcaspectacular","mcluz","mizuno35","mnzie01","mochi3","morenxo","nabilswap","nekbungoeng","nellysteem","nodzz","nurudeen081","oan-iata","oliver-liam","olenaginal","ontarget0","owleeya","peazy001","pictz","poundrickshaw","princedave12","quimby-art","raquel19","realmaya","sintiana","starksteem","steps100","tailah.bayu1","technoart","techy22","tember","twenty4","v0lga","vareya","weenyqueen","weirdartist","whizchick","yoe1974"]


def _downloadImagesFromParsedComments(parsedComments: list, thumbnailWidth: int) -> list:
    """
    Downloads all thumbnails noted in a parsedComments list.

    :param parsedComments: A list of parsedComments.
    :return: A list of enhanced parsedComment dict objects.
    """
    parsedCommentsOut = []
    unprocessed = 0
    print('Progress:', end=' ')
    for parsedComment in parsedComments:
        if IGNORE_DEFAULT_IMAGES_IN_POSTER and parsedComment['isDefaultImage']:
            continue

        parsedComment = _downloadImageFromParsedComment(parsedComment, thumbnailWidth)
        if not parsedComment:
            unprocessed += 1
            continue

        parsedCommentsOut.append(parsedComment)
        print('.', end='')

    if unprocessed > 0:
        print('Images not loadable(skipped): {imageAmount}\n'.format(imageAmount=unprocessed))

    return parsedCommentsOut


def _downloadImageFromParsedComment(parsedComment: dict, thumbnailWidth: int) -> dict:
    """
    Downlads a thumbnail image noted in a parsedComment dictionary.

    :param parsedComment A dictionary of thumbnail/image data.
    :return: Enhanced parsedComment dict object that has then an additional 'imageObject' field.
    """
    parsedComment['imageObject'] = None
    buffer = tempfile.SpooledTemporaryFile(max_size=1e9)
    r = requests.get(
        'https://images.hive.blog/{x}x0/'.format(x=thumbnailWidth) + parsedComment['imageUrl'],
        stream=True)
    if r.status_code == 200:
        downloaded = 0
        for chunk in r.iter_content(chunk_size=1024):
            downloaded += len(chunk)
            buffer.write(chunk)
        buffer.seek(0)
        parsedComment['imageObject'] = Image.open(io.BytesIO(buffer.read()))
    else:
        parsedComment = None
    buffer.close()

    return parsedComment


def _calculateImageHeightByParsedComments(parsedCommentsWithImages: list, columns: int) -> int:
    """
    Calculates the height of a thumbnail poster.

    :param parsedCommentsWithImage: A list of parsedComments which has additional imageObject fields.
    :return: The height of the thumbnail grid inclusive margins.
    """
    height = THUMBNAIL_MARGIN_IN_IMAGE
    col = 0
    largest = 0
    for parsedComment in parsedCommentsWithImages:
        imageHeight = parsedComment['imageObject'].size[1] + THUMBNAIL_MARGIN_IN_IMAGE
        col += 1
        if col >= columns:
            height += largest
            col = 0
            largest = 0
        else:
            if largest < imageHeight:
                largest = imageHeight

    if col > 0:
        height += largest + THUMBNAIL_MARGIN_IN_IMAGE

    return height + THUMBNAIL_MARGIN_IN_IMAGE


def _createThumbnailPoster(parsedCommentsWithImage: list, thumbnailWidth: int, columns: int) -> bool:
    """
    Creates a thumbnail poster from all thumbnail in a parsedCommentsWithImage list.

    :param parsedCommentsWithImage: A list of parsedComments which has additional imageObject fields.
    :return: True on success.
    """
    hostImage = Image.new(
        mode="RGBA",
        size=(
            ((thumbnailWidth + THUMBNAIL_MARGIN_IN_IMAGE) * columns) + THUMBNAIL_MARGIN_IN_IMAGE,
            _calculateImageHeightByParsedComments(parsedCommentsWithImage, columns)
        ),
        color=THUMBNAIL_POSTER_COLOR
    )
    xy = (THUMBNAIL_MARGIN_IN_IMAGE, THUMBNAIL_MARGIN_IN_IMAGE)
    col = 0
    # fnt = ImageFont.load_default()
    fnt = ImageFont.truetype("MadhouseCC0.ttf", 16)
    draw = ImageDraw.Draw(hostImage)
    largest = 0
    for parsedComment in parsedCommentsWithImage:
        thumbnail: Image = parsedComment['imageObject']
        hostImage.paste(thumbnail, xy)
        draw.text((xy[0] + 3, xy[1] + 3), parsedComment['author'], width=MAX_THUMBNAIL_WIDTH_IN_IMAGE,
                  fill=(0, 0, 0), font=fnt)
        draw.text((xy[0] + 2, xy[1] + 2), parsedComment['author'], width=MAX_THUMBNAIL_WIDTH_IN_IMAGE,
                  fill=THUMBNAIL_LABEL_COLOR, font=fnt)
        xy = (xy[0] + THUMBNAIL_MARGIN_IN_IMAGE + thumbnail.size[0], xy[1])
        col += 1
        if largest < thumbnail.size[1]:
            largest = thumbnail.size[1]
        if col >= MAX_THUMBNAILS_PER_ROW_IN_IMAGE:
            col = 0
            xy = (THUMBNAIL_MARGIN_IN_IMAGE, xy[1] + THUMBNAIL_MARGIN_IN_IMAGE + largest)
            largest = 0

    hostImage.save('GeneratedThumbnailPoster.png')

    return True


def _fetchComments(hiveLink: str) -> list:
    """
    Fetches all comments of a specific hive post.

    :param hiveLink: A Hive post link. Example: @user/this-is-a-post-permlink
    :return: A list of all comments of the post on success. Otherwise None.
    """
    hive = beem.Hive('https://api.deathwing.me')

    try:
        post = Comment(hiveLink, blockchain_instance=hive)
    except ValueError:
        return None

    return post.get_all_replies()


def _findByRegex(text: str, regex: str) -> str:
    """
    Finds and retrieves a string by a specific regex statement in a text.

    :param text: The source text.
    :param regex: The regex statement.
    :return: The text found on success. Otherwise an empty string.
    """

    matches = re.search(regex, text, re.MULTILINE)
    if not matches:
        return ''
    try:
        return '' if not matches.group(1) else matches.group(1)
    except IndexError:
        return ''


def _parseCommentBody(comment: Comment):
    """
    Parses a single comment body for finding imageUrl, postUrl and author.

    :param comment: A beem comment.
    :return: A parsed comment.
    """

    return {
        'postUrl': _findByRegex(comment.body, REGEX_POST_URL),
        'imageUrl': _findByRegex(comment.body, REGEX_IMAGE_URL).replace('https://images.hive.blog/0x0/', ''),
        'author': comment.author
    }


def _parseComments(comments: list) -> list:
    """
    Parses a list of beem comments.

    :param comments: A list of beem comments.
    :return: A list of parsed comments on success.
    """

    parsedComments = []

    for comment in comments:
        if comment.author in AUTHOR_BLACKLIST:
            continue

        parsedComment = _parseCommentBody(comment)
        parsedComment['isDefaultImage'] = False
        if not parsedComment['postUrl']:
            continue

        parsedComment['postUrl'] = parsedComment['postUrl'].replace('https://hive.blog', 'https://peakd.com')
        parsedComment['postUrl'] = parsedComment['postUrl'].replace('https://ecency.com', 'https://peakd.com')

        hivePermlink = parsedComment['postUrl'].replace('https://peakd.com/hive-174695/', '')

        try:
            hiveComment = Comment(hivePermlink)
            if 'lmac' not in str(hiveComment.get_votes()):
                print('Post {post} not voted by LMAC.'.format(post=hivePermlink))
                continue
        except:
            print('Failed to load {post}'.format(post=hivePermlink))
            continue

        if not parsedComment['imageUrl']:
            parsedComment['imageUrl'] = DEFAULT_IMAGE_URL
            parsedComment['isDefaultImage'] = True

        parsedComments.append(parsedComment)

    return parsedComments


def _loadTemplateFile(filename: str) -> str:
    """
    Loads a template file from disk.

    :param filename: The path and the name of the file.
    :return: The string containing the content of the file on success. Otherwise None.
    """

    if not os.path.isfile(filename):
        return None

    textFile = open(filename, "r")
    content = textFile.read()
    textFile.close()

    return content


def _createMarkdownFromParsedComments(parsedComments: list) -> str:
    """
    Generates a markdown from a list of parsed comments.

    :param parsedComments: A list of parsed comments like [{'postUrl': 'http://...', 'imageUrl': 'http://...', 'author': '@author'}, ...]
    :return: A string containing the markdown on success. Otherwise False.
    """

    bodyTemplate = _loadTemplateFile('template_md_body.tpl')
    imageTemplate = _loadTemplateFile('template_md_image.tpl')
    if not bodyTemplate or not imageTemplate:
        return False

    images = ''

    for parsedComment in parsedComments:
        images += imageTemplate.format(
            postUrl=parsedComment['postUrl'],
            imageUrl=parsedComment['imageUrl'],
            author=parsedComment['author']
        )

    return bodyTemplate.format(images=images)


def _createHtmlMarkupFromParsedComments(parsedComments: list) -> str:
    """
    Generates a HTML markup from a list of parsed comments.

    :param parsedComments: A list of parsed comments like [{'postUrl': 'http://...', 'imageUrl': 'http://...', 'author': '@author'}, ...]
    :return: A string containing the markup on success. Otherwise False.
    """

    bodyTemplate = _loadTemplateFile('template_html_body.tpl')
    imageTemplate = _loadTemplateFile('template_html_image.tpl')
    if not bodyTemplate or not imageTemplate:
        return False

    images = ''

    for parsedComment in parsedComments:
        if not parsedComment['imageUrl'] and not parsedComment['postUrl']:
            continue

        image = imageTemplate.replace('{postUrl}', parsedComment['postUrl'])
        image = image.replace('{imageUrl}', parsedComment['imageUrl'])
        image = image.replace('{author}', parsedComment['author'])

        images += image

    return bodyTemplate.replace('{images}', images)


def _saveMarkdownToDisk(markdown: str, saveAsHTMLFile: bool, specificName = None) -> bool:
    """
    Saves a generated markdown to disk.

    :param markdown: A string containing the markdown.
    :param saveAsHTMLFile: A boolean indicating whether the file should be saved as HTML file.
    :return: True on success.
    """

    extension = '.html' if saveAsHTMLFile else 'md'
    nowDate = datetime.datetime.now()

    textFile = open(specificName if specificName != None else nowDate.strftime("%m-%d-%Y-%H-%M") + '-GeneratedImageSheet' + extension, "w")
    if not textFile:
        return False
    textFile.write(markdown)
    textFile.close()

    return True


def main(args: dict) -> int:
    """
    Main function.

    :param args: A dictionary of command line arguments.
    :return: Exit code.
    """

    print('Fetching comments...')
    comments = _fetchComments(args['a'])
    if not comments:
        print('Error. Couldn\'t load post.')
        return 1

    print('Found {x} comments.'.format(x=len(comments)))

    print('Parsing comments...')
    parsedComments = _parseComments(comments)
    if not parsedComments:
        print('Error. Couldn\'t parse comments.')
        return 1

    print('Found and parsed {x} relevant comments.'.format(x=len(parsedComments)))

    if args['img']:
        print('Downloading images...')
        parsedCommentsWithImages = _downloadImagesFromParsedComments(parsedComments, args['thumbwidth'])
        print('Generating image...')
        if _createThumbnailPoster(parsedCommentsWithImages, args['thumbwidth'], args['columns']):
            print('Image successfully created!')
        else:
            print('Error. Couldn\'t create thumbnail image poster.')
            return 1
    else:
        print('Generating markdown...')
        markdown = None
        if args['html']:
            markdown = _createHtmlMarkupFromParsedComments(parsedComments)
        else:
            markdown = _createMarkdownFromParsedComments(parsedComments)
        if not markdown:
            print('Error. Couldn\'t create markdown. Insufficient data.')
            return 1

        print('Saving markdown to disk...')
        if not _saveMarkdownToDisk(markdown, args['html'], args['filename']):
            print('Error. Couldn\'t save markdown.')
            return 1

        print('Markdown successfully created!')

    return 0


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.description = 'Renders a markdown (or markup) from all entries submitted via comments in a contest ' \
                         'announcement post. '
    parser.add_argument(
        '-a',
        type=str,
        help='Hive url of a post. Syntax: \'contestthumbnailer.py -a "@user/permlink"\'.',
        required=True
    )
    parser.add_argument(
        '-html',
        type=bool,
        help='Generates a HML file. Syntax: \'contestthumbnailer.py -html 1 -a "@user/permlink"\'.',
        default=False,
        required=False
    )
    parser.add_argument(
        '-img',
        type=bool,
        help='Generates a image file. Syntax: \'contestthumbnailer.py -img 1 -a "@user/permlink"\'.',
        default=False,
        required=False
    )
    parser.add_argument(
        '-columns',
        type=int,
        help='Amount of thumbnails per row in a thumbnail poster. Syntax: \'contestthumbnailer.py -img 1 -columns 10 -a "@user/permlink"\'.',
        default=MAX_THUMBNAILS_PER_ROW_IN_IMAGE,
        required=False
    )
    parser.add_argument(
        '-thumbwidth',
        type=int,
        help='Width of a thumbnail in a thumbnail poster. Syntax: \'contestthumbnailer.py -img 1 -thumbwidth 160 -a "@user/permlink"\'.',
        default=MAX_THUMBNAIL_WIDTH_IN_IMAGE,
        required=False
    )
    parser.add_argument(
        '-filename',
        type=str,
        help='Specific filename for the output (Overrides default(generated names)).',
        default=None,
        required=False
    )
    exit(
        main(
            vars(
                parser.parse_args()
            )
        )
    )
