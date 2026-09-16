"""The dark token block exists twice, and the two copies must say the same thing.

web/tokens.css declares the dark values once for an explicit choice (`:root[data-theme="dark"]`) and once for
the browser preference (`@media (prefers-color-scheme: dark)` with no light override). CSS has no way to share
one block between a selector and a media query, so the duplication is real and this check is what keeps it from
drifting: it parses both blocks and compares every declaration, and it fails if one gains a value the other does
not have.
"""
import re
from pathlib import Path

TOKENS = Path(__file__).resolve().parents[1] / "web" / "tokens.css"


def declarations(block):
    """Every `--name: value` pair in a block, whitespace-normalised."""
    pairs = {}
    for name, value in re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+);", block):
        pairs[name] = " ".join(value.split()).lower()
    return pairs


def block_after(text, opener):
    start = text.index(opener)
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    raise AssertionError("unbalanced block for " + opener)


def test_the_two_dark_blocks_declare_the_same_values():
    text = TOKENS.read_text(encoding="utf-8")
    explicit = declarations(block_after(text, ":root[data-theme='dark']"))
    preferred = declarations(block_after(text, "@media (prefers-color-scheme: dark)"))
    assert explicit, "the explicit dark block declares nothing"
    assert preferred, "the preferred-scheme dark block declares nothing"
    assert explicit == preferred, (
        "the dark tokens have drifted: only explicit " + str(sorted(set(explicit) - set(preferred))) +
        "; only preference " + str(sorted(set(preferred) - set(explicit))) +
        "; different values " + str(sorted(name for name in set(explicit) & set(preferred) if explicit[name] != preferred[name]))
    )


def test_the_preferred_block_leaves_an_explicit_choice_alone():
    text = TOKENS.read_text(encoding="utf-8")
    preferred = block_after(text, "@media (prefers-color-scheme: dark)")
    guard = preferred[:preferred.index("{", preferred.index(":root"))]
    assert "data-theme='light'" in guard or 'data-theme="light"' in guard, (
        "the preference block must not override a reader who chose the light theme")

