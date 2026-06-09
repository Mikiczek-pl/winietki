"""Tools for creating personalized place cards from a PDF template."""

from .placecards import (
    PlacecardError,
    PlacecardSettings,
    TemplateTextField,
    TemplateTextStyle,
    create_placecards_pdf_bytes,
    create_placecards_pdf_file,
    inspect_template_fields,
    inspect_template_text,
    normalize_people,
    resolve_font_path,
)

__all__ = [
    "PlacecardError",
    "PlacecardSettings",
    "TemplateTextField",
    "TemplateTextStyle",
    "create_placecards_pdf_bytes",
    "create_placecards_pdf_file",
    "inspect_template_fields",
    "inspect_template_text",
    "normalize_people",
    "resolve_font_path",
]
