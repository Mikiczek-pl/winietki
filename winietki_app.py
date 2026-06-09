from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path

import fitz
import streamlit as st
from PIL import Image

from cr_placecards import PlacecardError, create_placecards_pdf_bytes, normalize_people


APP_NAME = "CR Winietki"


@dataclass(frozen=True)
class PlacecardTemplate:
    key: str
    name: str
    category: str
    price: float
    pdf_file: str
    font_file: str
    fields: tuple[dict, ...] = ()


TEMPLATES: tuple[PlacecardTemplate, ...] = (
    PlacecardTemplate("S-01", "S-01", "Standard", 1.50, "template_05.pdf", "Gabriola.ttf"),
    PlacecardTemplate("S-02", "S-02", "Standard", 1.50, "template_04.pdf", "BirchStd.otf"),
    PlacecardTemplate("S-03", "S-03", "Standard", 1.50, "template_07.pdf", "GreatVibes-Regular.otf"),
    PlacecardTemplate("S-04", "S-04", "Standard", 1.50, "template_11.pdf", "Italianno-Regular.ttf"),
    PlacecardTemplate("S-05", "S-05", "Standard", 1.50, "template_09.pdf", "BickhamScriptPro-Regular.otf"),
    PlacecardTemplate("S-06", "S-06", "Standard", 1.50, "template_12.pdf", "MilasianCircaMediumPERSONAL.ttf"),
    PlacecardTemplate("S-07", "S-07", "Standard", 1.50, "template_10.pdf", "Hijrnotes_PERSONAL_USE_ONLY.ttf"),
    PlacecardTemplate("S-08", "S-08", "Standard", 1.50, "template_08.pdf", "Beyond Infinity - Demo.ttf"),
    PlacecardTemplate("S-09", "S-09", "Standard", 1.50, "template_13.pdf", "Northwell-Regular.ttf"),
    PlacecardTemplate("S-10", "S-10", "Standard", 1.50, "template_06.pdf", "cambria.ttc"),

    PlacecardTemplate("O-01", "O-01", "Ozdobne", 1.50, "template_03.pdf", "Gabriola.ttf"),
    PlacecardTemplate("O-02", "O-02", "Ozdobne", 1.50, "template_16.pdf", "Aphrodite Slim Text.ttf"),
    PlacecardTemplate("O-03", "O-03", "Ozdobne", 1.50, "template_22.pdf", "Allura-Regular.otf"),

    PlacecardTemplate(
        "O-04",
        "O-04",
        "Ozdobne",
        1.50,
        "template_02.pdf",
        "Northwell-Regular.ttf",
        (
            {
                "bbox": (44.0, 171.0, 211.0, 238.0),
                "erase_bbox": (38.0, 164.0, 218.0, 246.0),
                "font_name": "Northwell-Regular",
                "font_size_pt": 43.0,
                "color_rgb": (0, 0, 0),
                "remove_graphics": True,
                "max_width_pt": 168.0,
            },
            {
                "bbox": (44.0, 36.0, 211.0, 103.0),
                "erase_bbox": (38.0, 28.0, 218.0, 111.0),
                "font_name": "Northwell-Regular",
                "font_size_pt": 43.0,
                "color_rgb": (0, 0, 0),
                "rotation": 180,
                "remove_graphics": True,
                "max_width_pt": 168.0,
            },
        ),
    ),

    PlacecardTemplate(
        "O-05",
        "O-05",
        "Ozdobne",
        1.50,
        "template_15.pdf",
        "Dynalight-Regular.otf",
        (
            {
                "bbox": (31.0, 158.0, 224.0, 266.0),
                "erase_bbox": (50.0, 178.0, 206.0, 234.0),
                "font_name": "Dynalight-Regular",
                "font_size_pt": 39.292,
                "color_rgb": (0, 0, 0),
                "remove_graphics": True,
                "underline_mode": "o05",
                "max_width_pt": 182.0,
            },
        ),
    ),

    PlacecardTemplate("D-01", "D-01", "Dekoracyjne", 1.80, "template_24.pdf", "Aphrodite Slim Text.ttf"),
    PlacecardTemplate("D-02", "D-02", "Dekoracyjne", 1.80, "template_26.pdf", "BirchStd.otf"),
    PlacecardTemplate("D-03", "D-03", "Dekoracyjne", 1.80, "template_28.pdf", "BASKVILL.ttf"),
    PlacecardTemplate("D-04", "D-04", "Dekoracyjne", 1.80, "template_14.pdf", "Aphrodite Slim Text.ttf"),
    PlacecardTemplate("D-05", "D-05", "Dekoracyjne", 1.80, "template_30.pdf", "GreatVibes-Regular.otf"),
    PlacecardTemplate("D-07", "D-07", "Dekoracyjne", 1.80, "template_18.pdf", "Allura-Regular.otf"),
    PlacecardTemplate("D-08", "D-08", "Dekoracyjne", 1.80, "template_23.pdf", "AGaramondPro-Italic.otf"),
    PlacecardTemplate("D-09", "D-09", "Dekoracyjne", 1.80, "template_01.pdf", "GreatVibes-Regular.otf"),
    PlacecardTemplate("D-10", "D-10", "Dekoracyjne", 1.80, "template_27.pdf", "BASKVILL.ttf"),
    PlacecardTemplate("D-11", "D-11", "Dekoracyjne", 1.80, "template_17.pdf", "AGaramondPro-Italic.otf"),
    PlacecardTemplate("D-12", "D-12", "Dekoracyjne", 1.80, "template_25.pdf", "Aphrodite Slim Text.ttf"),

    PlacecardTemplate("Z-01", "Z-01", "Zlote", 3.00, "template_19.pdf", "Dynalight-Regular.otf"),
    PlacecardTemplate("Z-04", "Z-04", "Zlote", 3.00, "template_29.pdf", "Allura-Regular.otf"),

    PlacecardTemplate(
        "Z-05",
        "Z-05",
        "Zlote",
        3.00,
        "template_21.pdf",
        "GreatVibes-Regular.otf",
        (
            {
                "bbox": (55.0, 191.0, 200.0, 240.0),
                "font_name": "GreatVibes-Regular",
                "font_size_pt": 28.0,
                "color_rgb": (190, 145, 61),
                "max_width_pt": 160.0,
            },
        ),
    ),

    PlacecardTemplate(
        "Z-06",
        "Z-06",
        "Zlote",
        3.00,
        "template_20.pdf",
        "GreatVibes-Regular.otf",
        (
            {
                "bbox": (70.0, 174.0, 185.0, 256.0),
                "erase_bbox": (80.0, 170.0, 174.0, 258.0),
                "font_name": "GreatVibes-Regular",
                "font_size_pt": 31.104,
                "color_rgb": (190, 145, 61),
                "max_width_pt": 120.0,
                "force_two_lines": True,
            },
        ),
    ),
)


CATEGORY_ORDER = ("Standard", "Ozdobne", "Dekoracyjne", "Zlote")


def app_resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def template_pdf_path(template: PlacecardTemplate) -> Path:
    return app_resource_path("assets", "placecard_templates", template.pdf_file)


def template_font_path(template: PlacecardTemplate) -> Path:
    return app_resource_path("assets", "placecard_fonts", template.font_file)


def format_money(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " zł"


@st.cache_data(show_spinner=False)
def render_template_preview(pdf_path_str: str) -> bytes | None:
    pdf_path = Path(pdf_path_str)

    if not pdf_path.exists():
        return None

    try:
        doc = fitz.open(pdf_path)
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(0.8, 0.8), alpha=False)
        image_bytes = pix.tobytes("png")
        doc.close()
        return image_bytes
    except Exception:
        return None


def render_pdf_pages(pdf_bytes: bytes, max_pages: int = 12) -> list[bytes]:
    images: list[bytes] = []

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages_to_show = min(doc.page_count, max_pages)

    for index in range(pages_to_show):
        pix = doc[index].get_pixmap(matrix=fitz.Matrix(1.2, 1.2), alpha=False)
        images.append(pix.tobytes("png"))

    doc.close()
    return images


def get_template_by_key(key: str) -> PlacecardTemplate:
    for template in TEMPLATES:
        if template.key == key:
            return template

    raise PlacecardError("Nie znaleziono wybranego szablonu.")


def init_state() -> None:
    if "selected_template_key" not in st.session_state:
        st.session_state.selected_template_key = TEMPLATES[0].key

    if "generated_pdf" not in st.session_state:
        st.session_state.generated_pdf = None

    if "generated_count" not in st.session_state:
        st.session_state.generated_count = 0


def show_template_selector() -> PlacecardTemplate:
    st.subheader("1. Wybierz szablon")

    template_options = {
        f"{template.category} / {template.name} — {format_money(template.price)} / szt.": template.key
        for template in TEMPLATES
    }

    current_template = get_template_by_key(st.session_state.selected_template_key)

    current_label = None
    for label, key in template_options.items():
        if key == current_template.key:
            current_label = label
            break

    selected_label = st.selectbox(
        "Szablon",
        options=list(template_options.keys()),
        index=list(template_options.keys()).index(current_label),
    )

    selected_key = template_options[selected_label]
    st.session_state.selected_template_key = selected_key

    template = get_template_by_key(selected_key)

    preview_bytes = render_template_preview(str(template_pdf_path(template)))

    if preview_bytes:
        st.image(preview_bytes, caption=f"Podgląd szablonu {template.name}", width=260)
    else:
        st.warning(f"Brak podglądu. Sprawdź plik: {template.pdf_file}")

    return template


def show_people_input(template: PlacecardTemplate) -> list[str]:
    st.subheader("2. Wklej listę osób")

    people_raw = st.text_area(
        "Jedna osoba w jednym wierszu",
        height=260,
        placeholder="Anna Kowalska\nJan Nowak\nKatarzyna Wiśniewska",
    )

    names = normalize_people(people_raw)
    count = len(names)
    total = count * template.price

    st.info(f"Liczba osób: {count} | {format_money(template.price)} × {count} = {format_money(total)}")

    return names


def generate_pdf(template: PlacecardTemplate, names: list[str]) -> None:
    if not names:
        st.error("Wklej listę osób, po jednej osobie w wierszu.")
        return

    pdf_path = template_pdf_path(template)
    font_path = template_font_path(template)

    if not pdf_path.exists():
        st.error(f"Brakuje pliku szablonu: {pdf_path}")
        return

    if not font_path.exists():
        st.error(f"Brakuje pliku fontu: {font_path}")
        return

    progress_bar = st.progress(0)
    status = st.empty()

    def progress(done: int, total: int) -> None:
        progress_bar.progress(done / total)
        status.write(f"Generowanie: {done}/{total}")

    try:
        with st.spinner("Generuję PDF..."):
            pdf = create_placecards_pdf_bytes(
                pdf_path,
                names,
                font_path=font_path,
                template_fields=template.fields or None,
                progress=progress,
            )

        st.session_state.generated_pdf = pdf
        st.session_state.generated_count = len(names)

        progress_bar.progress(1.0)
        status.success("PDF gotowy.")

    except Exception as exc:
        st.session_state.generated_pdf = None
        st.session_state.generated_count = 0
        st.error(f"Błąd generowania: {exc}")


def show_generated_pdf(template: PlacecardTemplate) -> None:
    pdf = st.session_state.generated_pdf

    if not pdf:
        return

    count = st.session_state.generated_count
    total = count * template.price

    st.subheader("3. Pobierz gotowy PDF")
    st.success(f"Gotowe: {count} stron | razem: {format_money(total)}")

    st.download_button(
        label="Pobierz PDF",
        data=pdf,
        file_name=f"winietki_{template.name}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    st.subheader("Podgląd pierwszych stron")

    try:
        images = render_pdf_pages(pdf, max_pages=12)

        cols = st.columns(3)

        for index, image_bytes in enumerate(images):
            with cols[index % 3]:
                st.image(image_bytes, caption=f"Strona {index + 1}", use_container_width=True)

        if count > 12:
            st.caption("Pokazano tylko pierwsze 12 stron podglądu. PDF zawiera wszystkie strony.")

    except Exception as exc:
        st.warning(f"Nie udało się pokazać podglądu PDF: {exc}")


def main() -> None:
    st.set_page_config(
        page_title=APP_NAME,
        page_icon="🪪",
        layout="wide",
    )

    init_state()

    st.title(APP_NAME)
    st.caption("Generator winietek z gotowych szablonów PDF")

    left, right = st.columns([1, 1.3], gap="large")

    with left:
        template = show_template_selector()
        names = show_people_input(template)

        if st.button("Generuj PDF", type="primary", use_container_width=True):
            generate_pdf(template, names)

    with right:
        show_generated_pdf(template)

    with st.expander("Informacje techniczne"):
        st.write("Aplikacja korzysta z plików w folderach:")
        st.code(
            """
assets/placecard_templates/
assets/placecard_fonts/
            """.strip()
        )


if __name__ == "__main__":
    main()
