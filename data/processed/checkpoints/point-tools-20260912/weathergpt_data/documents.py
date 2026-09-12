"""Bounded PDF text extraction; extracted text never establishes current validity."""
import io
from .transport import SourceError


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
