import html as html_escaper

import mistune
from pygments import highlight
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

from interface.styles import Styles


# Single shared formatter instance — no need to rebuild per code block
_FORMATTER = HtmlFormatter(nowrap=True)

# Plain-text fallback lexer (renders code with zero highlighting, but never crashes)
_FALLBACK_LEXER = TextLexer(stripall=True)


class HighlightRenderer(mistune.HTMLRenderer):
    def block_code(self, code, info=None):
        """
        Intercepts markdown code blocks and colorizes them using Pygments classes.

        Resilience notes:
        - NEVER uses guess_lexer(): it's slow (statistical analysis on every
          streaming re-render) and raises ClassNotFound on partial/odd code,
          which would kill the entire render pipeline mid-stream.
        - Unknown or missing languages degrade gracefully to plain text.
        """
        lexer = _FALLBACK_LEXER

        if info:
            # Fence info can contain extras: ```python title="x" -> take first token only
            lang = info.strip().split()[0] if info.strip() else ""
            if lang:
                try:
                    lexer = get_lexer_by_name(lang, stripall=True)
                except ClassNotFound:
                    lexer = _FALLBACK_LEXER

        try:
            highlighted_code = highlight(code, lexer, _FORMATTER)
        except Exception:
            # Absolute last line of defense — escape raw code so HTML stays valid
            highlighted_code = html_escaper.escape(code)

        return f"<pre><code>{highlighted_code}</code></pre>"


# Instantiate global, optimized markdown compiler
markdown_compiler = mistune.Markdown(renderer=HighlightRenderer())


def markdown_to_html(text: str) -> str:
    """
    Converts a raw streaming markdown response string into fully custom-styled HTML.

    Guaranteed to never raise: if the markdown compiler chokes on a malformed
    partial stream state, we degrade to escaped plain text instead of crashing
    the GUI render loop.
    """
    if not text:
        return f"{Styles.CODE_HIGHLIGHT_CSS}<body></body>"

    try:
        raw_html = markdown_compiler(text)
    except Exception as e:
        print(f"[PARSER WARNING]: Markdown compile failed ({e}) -> degrading to plain text.")
        raw_html = f"<pre>{html_escaper.escape(text)}</pre>"

    # Wrap with our custom styles matrix so PyQt UI displays it perfectly
    return f"{Styles.CODE_HIGHLIGHT_CSS}<body>{raw_html}</body>"