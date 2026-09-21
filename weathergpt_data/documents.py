"""Bounded PDF text extraction; extracted text never establishes current validity."""
import io
import re
from .transport import SourceError


class DocumentPruned(Exception):
    """The document is still indexed, but its body is outside the retention window.

    Raised instead of a plain not-found so the caller can say what is retained
    (the hash and the extracted pages) rather than implying the document is unknown.
    """

    def __init__(self, sha, detail):
        super().__init__(detail)
        self.sha = sha
        self.detail = detail


UNMAPPED_GLYPH = re.compile(r'\(cid:\d+\)')


def strip_controls(value):
    """Publisher fonts can map to unprintable or surrogate code points; substitute and flag.

    An unmapped glyph arrives in two different shapes and both are the same failure. A code point the
    font maps to nothing is caught by the loop below. A glyph with no ToUnicode entry at all is handed
    over by the extractor as the literal ASCII text "(cid:0)", which the loop cannot see because every
    one of those characters is printable.

    Measured 21 September 2026: asked for the apple advisory in Shimla, the answer quoted the bulletin
    as "(cid:0) Collect and dispose of fallen and diseased fruit" - the publisher's own bullet, printed
    to the reader as extractor debris. It is substituted like any other unmapped glyph, and it sets the
    same damaged flag, so a passage that lost characters still says so rather than passing as clean.
    """
    value,replaced=UNMAPPED_GLYPH.subn(' ',value)
    out=[];damaged=bool(replaced)
    for character in value:
        code=ord(character)
        if code<9 or 11<=code<=12 or 14<=code<=31 or code==127 or 0xd800<=code<=0xdfff:
            out.append(' ');damaged=True
        else:out.append(character)
    return ''.join(out),damaged


def pdf_pages(body):
    if not body.startswith(b'%PDF'):raise SourceError('Expected bulletin PDF')
    from pypdf import PdfReader
    try:
        pdf=PdfReader(io.BytesIO(body))
        if pdf.is_encrypted:raise SourceError('Encrypted bulletin requires separate review')
        if not 1<=len(pdf.pages)<=150:raise SourceError('Bulletin must contain 1–150 pages')
        return [{'physical_page':i+1,'text':text,'source_locator':f'physical PDF page {i+1}',
                 'extraction_status':'text_extracted_reading_order_unverified' if text.strip() else 'ocr_required'}
                for i,page in enumerate(pdf.pages) for text in [page.extract_text() or '']]
    except SourceError:raise
    except Exception as exc:raise SourceError('Bulletin PDF cannot be parsed: '+str(exc)) from exc
