"""Shared UI styling for the Streamlit app."""

MINIMAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: #444;
}

.block-container {
    padding-top: 2rem;
    max-width: 1100px;
}

h1 {
    font-weight: 500 !important;
    font-size: 1.5rem !important;
    color: #333 !important;
    letter-spacing: -0.02em;
}

h2, h3 {
    font-weight: 500 !important;
    font-size: 1rem !important;
    color: #444 !important;
}

[data-testid="stCaptionContainer"] p {
    color: #888;
    font-size: 0.85rem;
    font-weight: 300;
}

.annotation-card {
    background: #FAFAFA;
    border: 1px solid #E8E8E8;
    border-radius: 6px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0 1.25rem 0;
    font-size: 0.78rem;
    color: #777;
    line-height: 1.5;
    font-weight: 300;
}

.section-label {
    font-size: 0.72rem;
    color: #999;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.35rem;
    font-weight: 400;
}

.measurement-block {
    margin-bottom: 2.5rem;
    padding-bottom: 1.5rem;
    border-bottom: 1px solid #F0F0F0;
}

.measurement-block:last-child {
    border-bottom: none;
}

div[data-testid="stDataFrame"] {
    border: none !important;
}

div[data-testid="stTabs"] button {
    font-size: 0.82rem;
    font-weight: 400;
    color: #666;
}

div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #333;
}

.stMultiSelect label, .stCheckbox label, .stDownloadButton label {
    font-size: 0.82rem !important;
    font-weight: 400 !important;
    color: #555 !important;
}

.stAlert {
    border: none !important;
    background: #FAFAFA !important;
    color: #777 !important;
    font-size: 0.82rem;
}
</style>
"""


def inject_styles() -> None:
    import streamlit as st
    st.markdown(MINIMAL_CSS, unsafe_allow_html=True)


def annotation_card(text: str) -> str:
    return f'<div class="annotation-card">{text}</div>'
