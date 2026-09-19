
from pathlib import Path

def rewrite(name, pairs):
    p = Path(name)
    t = p.read_text()
    for old, new in pairs:
        if old not in t:
            print('  MISS', name, old[:50].replace('\n', ' '))
            continue
        t = t.replace(old, new)
    p.write_text(t)
    print('rewrote', name)

rewrite('page.test.tsx', [
    ("import { QueryClient, QueryClientProvider } from '@tanstack/react-query';\nimport { render, screen } from '@testing-library/react';",
     "import { render, screen } from '@testing-library/react';"),
    ("import { AskSurface } from './AskSurface';\nimport { server } from '../test/msw';",
     "import { server } from '../test/msw';\nimport { renderAsk } from '../test/ask';"),
    ("function mount(node: React.ReactElement) {\n  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });\n  return render(<QueryClientProvider client={client}>{node}</QueryClientProvider>);\n}\n\n", ""),
    ('mount(<AskSurface language="" persona="" />);', 'renderAsk();'),
    ("const { container } = mount(<AnswerTurn packet={PACKET} onFollowUp={() => {}} />);",
     "const { container } = render(<AnswerTurn packet={PACKET} onFollowUp={() => {}} />);"),
])
