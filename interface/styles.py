from pygments.formatters import HtmlFormatter


# =====================================================================
# DESIGN TOKEN CONSTANTS
# Single source of truth for repeated color values.
# Change here → updates everywhere automatically.
# =====================================================================
_RED_PRIMARY    = "#ff3333"
_RED_DARK       = "#8b0000"
_RED_HOVER      = "#ff9999"
_BLUE_PRIMARY   = "#004d99"
_BG_DARK        = "rgba(18, 18, 20, 0.92)"
_BG_CONTAINER   = "rgba(20, 20, 22, 0.95)"
_BORDER_SUBTLE  = "#3a3a3c"
_TEXT_PRIMARY   = "#e0e0e0"
_TEXT_MUTED     = "#888888"


# =====================================================================
# AUTO-GENERATED PYGMENTS CSS
# Uses Pygments' own HtmlFormatter to generate a COMPLETE token CSS
# set — no manual class definitions that miss tokens.
# =====================================================================
def _generate_pygments_css() -> str:
    """
    Generates a full Pygments token CSS block using the 'monokai' style.
    This covers ALL token classes Pygments can emit — not just 7 of them.
    The result is wrapped in a <style> tag for direct HTML injection.
    """
    formatter = HtmlFormatter(style="monokai", nowrap=True)
    css_rules = formatter.get_style_defs()          # returns all .tokenclass { ... } rules

    # Override the default Pygments background so it matches our dark theme
    extra = f"""
        pre  {{ background-color: #121214; padding: 10px; border-radius: 5px;
                border: 1px solid #2d2d30; margin: 8px 0; overflow-x: auto; }}
        code {{ font-family: 'Fira Code', 'Consolas', monospace; font-size: 13px; }}
        body {{ background-color: transparent; color: {_TEXT_PRIMARY};
                font-family: 'Segoe UI', sans-serif; font-size: 14px;
                padding: 4px 8px; }}
        h1, h2, h3 {{ color: #ffffff; font-weight: bold; }}
        a  {{ color: #4da6ff; text-decoration: none; }}
        p  {{ margin: 6px 0; line-height: 1.6; }}
        strong {{ color: #ffffff; }}
        code {{ color: #f1fa8c; }}
    """
    return f"<style>\n{css_rules}\n{extra}\n</style>"


# Pre-compute once at import time — never regenerated per-render
CODE_HIGHLIGHT_CSS_BLOCK: str = _generate_pygments_css()


class Styles:
    # =====================================================================
    # FRAME STATE COLORS
    # =====================================================================
    BG_CONTAINER_ONLINE  = _BG_CONTAINER
    BG_CONTAINER_OFFLINE = "rgba(16, 16, 22, 0.95)"
    BORDER_ONLINE        = _RED_DARK
    BORDER_OFFLINE       = _BLUE_PRIMARY

    # =====================================================================
    # INPUT FIELD
    # =====================================================================
    INPUT_FIELD = f"""
        QLineEdit {{
            background-color: rgba(26, 26, 28, 0.85);
            color: #ffffff;
            border: 1px solid {_BORDER_SUBTLE};
            border-radius: 6px;
            padding: 10px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border: 1px solid {_RED_PRIMARY};
        }}
    """

    # =====================================================================
    # OUTPUT VIEW
    # Non-code prose uses proportional font (Segoe UI).
    # Code blocks inside use the monospace font set via CODE_HIGHLIGHT_CSS.
    # Scrollbar styled to match dark theme.
    # =====================================================================
    OUTPUT_VIEW = f"""
        QTextEdit {{
            background-color: {_BG_DARK};
            color: {_TEXT_PRIMARY};
            border: 1px solid #2a2a2c;
            border-radius: 6px;
            padding: 12px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            line-height: 1.6;
        }}
        QScrollBar:vertical {{
            background: #1a1a1c;
            width: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: #3a3a3c;
            border-radius: 4px;
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #555557;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar:horizontal {{
            background: #1a1a1c;
            height: 8px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: #3a3a3c;
            border-radius: 4px;
            min-width: 20px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: #555557;
        }}
        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}
    """

    # =====================================================================
    # UTILITY BUTTONS
    # =====================================================================
    UTILITY_BUTTON = """
        QPushButton {
            background-color: #222224;
            color: #bbbbbb;
            border: 1px solid #3e3e42;
            border-radius: 4px;
            padding: 5px 12px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2a2a2c;
            color: #ffffff;
            border: 1px solid #555557;
        }
        QPushButton:pressed {
            background-color: #1a1a1c;
            color: #aaaaaa;
            border: 1px solid #3e3e42;
        }
        QPushButton:disabled {
            color: #444446;
            border: 1px solid #2a2a2c;
        }
    """

    # =====================================================================
    # HALT BUTTON
    # =====================================================================
    HALT_BUTTON = f"""
        QPushButton {{
            background-color: rgba(139, 0, 0, 0.8);
            color: #ffffff;
            border: 1px solid {_RED_PRIMARY};
            border-radius: 6px;
            padding: 6px 15px;
            font-family: 'Segoe UI', sans-serif;
            font-size: 12px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: rgba(255, 51, 51, 0.9);
            border: 1px solid {_RED_HOVER};
        }}
        QPushButton:pressed {{
            background-color: rgba(200, 0, 0, 1.0);
        }}
        QPushButton:disabled {{
            background-color: rgba(80, 0, 0, 0.6);
            color: #888888;
            border: 1px solid #550000;
        }}
    """

    # =====================================================================
    # VOICE CHECKBOX
    # =====================================================================
    VOICE_CHECKBOX = f"""
        QCheckBox {{
            color: {_TEXT_MUTED};
            font-family: 'Segoe UI', sans-serif;
            font-size: 10px;
            font-weight: bold;
            spacing: 5px;
        }}
        QCheckBox::indicator {{
            width: 12px;
            height: 12px;
            border: 1px solid #444444;
            background: #1a1a1c;
            border-radius: 3px;
        }}
        QCheckBox::indicator:checked {{
            background: {_RED_PRIMARY};
            border: 1px solid {_RED_HOVER};
        }}
        QCheckBox:disabled {{
            color: #444446;
        }}
        QCheckBox::indicator:disabled {{
            background: #1a1a1c;
            border: 1px solid #2a2a2c;
        }}
    """

    # =====================================================================
    # CODE HIGHLIGHT CSS (pre-computed, injected once per document)
    # =====================================================================
    CODE_HIGHLIGHT_CSS = CODE_HIGHLIGHT_CSS_BLOCK

    # =====================================================================
    # DYNAMIC FRAME STYLE
    # =====================================================================
    @classmethod
    def get_frame_style(cls, is_online: bool) -> str:
        bg     = cls.BG_CONTAINER_ONLINE  if is_online else cls.BG_CONTAINER_OFFLINE
        border = cls.BORDER_ONLINE        if is_online else cls.BORDER_OFFLINE
        return f"""
            QWidget#ContainerFrame {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 12px;
            }}
        """