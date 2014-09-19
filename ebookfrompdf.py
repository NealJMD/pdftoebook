import argparse
import os
from ebooklib import epub
import subprocess as sp
import re

from pdfminer.pdfinterp import PDFResourceManager, process_pdf
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from cStringIO import StringIO

DEFAULT_STRING = "unknown"
CHAPTER_REGEX = '(?:\n\s*?\n\s*?|chapter\s*|\f\s*?)[0-9cxviXVIC]+\s*?\n\s*?'
NEWLINE_REGEX = "\r*\n"
HYPHEN_REGEX = "-\s+"
PAGEBREAK_REGEX = "\f"#"(?:(?:"+NEWLINE_REGEX+")*\s*\f+\s*(?:"+NEWLINE_REGEX+")*)+"
CANONICAL_NEWLINE = "\n"

MIN_TEXT_LINE_LENGTH = 10
MAX_PARAGRAPH_END_LINE_FRACTION = 0.8

CODEC = "utf-8"

def wrap_p_tags(text):
    return "<p>"+text+"</p>"

def log(*args):
    print args

def read_text_from_filepath(path):
    rsrcmgr = PDFResourceManager()
    retstr = StringIO()
    laparams = LAParams()
    device = TextConverter(rsrcmgr, retstr, codec=CODEC, laparams=laparams)

    fp = file(path, 'rb')
    process_pdf(rsrcmgr, device, fp)
    fp.close()
    device.close()

    string = retstr.getvalue()
    retstr.close()
    return string

def add_metadata(book, metadata):
    if 'language' not in metadata: metadata['language'] = 'english'
    if 'title' in metadata: book.set_title(metadata['title'])
    if 'language' in metadata: book.set_language(metadata['language'])
    if 'identifier' in metadata: book.set_identifier(metadata['identifier'])
    if 'author' in metadata: book.add_author(metadata['author'])

def typical_text_line_length(lines):
    count, total = 0, 0
    for minimum in [MIN_TEXT_LINE_LENGTH, 0]:
        for line in lines:
            if len(line) < minimum: continue
            count += 1
            total += len(line)
        if count > 0: break            
    return float(total)/count

def clean_hyphens(text):
    return "".join(re.split(HYPHEN_REGEX, text))

def clean_newlines(text):
    debroken = re.split(PAGEBREAK_REGEX, unicode(text, CODEC), re.UNICODE)
    log("Split chapter into", len(debroken), "pages")
    without_pagebreaks = CANONICAL_NEWLINE.join(debroken)
    lines = re.split(NEWLINE_REGEX, without_pagebreaks)
    if len(lines) == 0: return ""
    typical_length = typical_text_line_length(lines)
    paragraphs = []
    start = 0
    while start < len(lines):
        end = start
        while end < len(lines) and len(lines[end]) >= MAX_PARAGRAPH_END_LINE_FRACTION * typical_length:
            end += 1
        paragraphs.append(" ".join(lines[start:end+1]))
        start = end + 1
    paragraphs = map(clean_hyphens, paragraphs)
    log("Split chapter into", len(paragraphs), "paragraphs")
    return "".join(map(wrap_p_tags, paragraphs))

def create_chapters_from_text(full_text):
    split_on_chapter = re.split(CHAPTER_REGEX, full_text, flags=re.IGNORECASE)
    chapters = [split_on_chapter[0]]
    for ii in range(1, len(split_on_chapter)-1, 2):
        chapters.append(split_on_chapter[ii] + split_on_chapter[ii+1])
    return map(clean_newlines, chapters)

def create_epub_from_text(full_text, metadata={}):
    book = epub.EpubBook()
    add_metadata(book, metadata)
    chapters = create_chapters_from_text(full_text)
    chapter_objects = []
    for ii, chapter in enumerate(chapters):
        c = epub.EpubHtml(title="arbitrary"+str(ii), file_name="arbitrary"+str(ii)+".xhtml")
        c.content = chapter
        chapter_objects.append(c)
    for c in chapter_objects:
        book.add_item(c)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapter_objects
    return book

def create_metadata_from_args(args):
    metadata = {}
    metadata['author'] = args.author
    metadata['title'] = args.title
    if metadata['title'] == DEFAULT_STRING:
        metadata['title'] = os.path.basename(args.pdf)
    return metadata

def switch_extension(filepath, desired_ext):
    root, ext = os.path.splitext(filepath)
    return root + "." + desired_ext

def create_kindle_from_epub(filepath):
    sp.call(["./kindlegen", filepath])

def main(args):
    full_text = read_text_from_filepath(args.pdf)
    metadata = create_metadata_from_args(args)
    book = create_epub_from_text(full_text, metadata)
    epub_filepath = switch_extension(args.pdf, "epub")
    epub.write_epub(epub_filepath, book, {})
    create_kindle_from_epub(epub_filepath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert pdf to ebook.')
    parser.add_argument('pdf', metavar='pdf', type=str,
                       help='the pdf file to read from')
    parser.add_argument('--title', metavar='title', type=str, default=DEFAULT_STRING,
                       help='the pdf file to read from')
    parser.add_argument('--author', metavar='author', type=str, default=DEFAULT_STRING,
                       help='the pdf file to read from')

    args = parser.parse_args()
    main(args)
