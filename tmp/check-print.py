import sys
from pypdf import PdfReader
path = 'research/reviews/frontend-v2-20260915/after/print-assistant.pdf'
reader = PdfReader(path)
pages = [page.extract_text() or '' for page in reader.pages]
print('pages:', len(pages))
joined = '\n'.join(pages)
checks = {
    'has answer heading': 'Answer' in joined,
    'has forecast value': 'mm' in joined or 'FORECAST' in joined.upper(),
    'composer placeholder present': 'Will it rain in Ahmedabad tomorrow morning?' in joined,
    'composer buttons present': 'Match my question' in joined,
    'masthead present': 'Search a place' in joined,
    'colophon present': 'Geometry from the India Meteorological Department' in joined,
    'appearance chip present': 'System · day' in joined or 'Day desk' in joined,
}
for name, value in checks.items():
    print(('%-32s %s') % (name, value))
print('---- first 220 characters of page 1 ----')
print(pages[0][:220].replace('\n', ' | '))
