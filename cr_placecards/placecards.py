from __future__ import annotations

import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import fitz
from PIL import Image, ImageDraw, ImageFont


ProgressCallback = Callable[[int, int], None]


class PlacecardError(RuntimeError):
    """Raised when place cards cannot be created from the supplied template."""


@dataclass(frozen=True)
class PlacecardSettings:
    horizontal_margin_pt: float = 18.0
    erase_padding_pt: float = 3.0
    min_font_size_pt: float = 14.0
    line_gap_factor: float = 1.02
    raster_dpi: int = 600

    def validate(self) -> None:
        if self.horizontal_margin_pt < 0:
            raise PlacecardError("Margines pola tekstowego nie moze byc ujemny.")
        if self.erase_padding_pt < 0:
            raise PlacecardError("Margines czyszczenia tekstu nie moze byc ujemny.")
        if self.min_font_size_pt <= 0:
            raise PlacecardError("Minimalny rozmiar fontu musi byc wiekszy od 0.")
        if self.line_gap_factor <= 0:
            raise PlacecardError("Odstep miedzy wierszami musi byc wiekszy od 0.")
        if self.raster_dpi < 144:
            raise PlacecardError("DPI napisu musi miec co najmniej 144.")


@dataclass(frozen=True)
class TemplateTextStyle:
    text: str
    font_name: str
    font_size_pt: float
    color_rgb: tuple[int, int, int]
    bbox: tuple[float, float, float, float]
    page_width_pt: float
    page_height_pt: float
    rotation: int = 0
    max_width_pt: float | None = None
    erase_bbox: tuple[float, float, float, float] | None = None
    remove_graphics: bool = False
    underline_mode: str | None = None
    force_two_lines: bool = False

    @property
    def center_x(self) -> float:
        return (self.bbox[0] + self.bbox[2]) / 2.0

    @property
    def center_y(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2.0


TemplateTextField = TemplateTextStyle


class _RasterFont:
    def __init__(self, font_path: Path, dpi: int) -> None:
        self.font_path = font_path
        self.dpi = dpi
        self._cache: dict[float, ImageFont.FreeTypeFont] = {}
        self._draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))

    def get(self, size_pt: float) -> ImageFont.FreeTypeFont:
        rounded_size = round(size_pt * 2.0) / 2.0
        if rounded_size not in self._cache:
            size_px = max(1, int(round(rounded_size * self.dpi / 72.0)))
            self._cache[rounded_size] = ImageFont.truetype(str(self.font_path), size_px)
        return self._cache[rounded_size]

    def text_length_pt(self, text: str, size_pt: float) -> float:
        font = self.get(size_pt)
        return float(self._draw.textlength(text, font=font) * 72.0 / self.dpi)


def normalize_people(raw_text: str | Iterable[str]) -> list[str]:
    if isinstance(raw_text, str):
        lines = raw_text.splitlines()
    else:
        lines = list(raw_text)

    people: list[str] = []
    for line in lines:
        name = " ".join(str(line).strip().split())
        if name:
            people.append(name)
    return people


def inspect_template_text(template_pdf: str | Path, placeholder_text: str | None = None) -> TemplateTextStyle:
    return inspect_template_fields(template_pdf, placeholder_text=placeholder_text)[0]


def inspect_template_fields(template_pdf: str | Path, placeholder_text: str | None = None) -> list[TemplateTextField]:
    doc = _open_pdf(Path(template_pdf))
    try:
        page = doc[0]
        lines = _text_lines(page)
        if not lines:
            raise PlacecardError("Szablon musi zawierac przykladowe nazwisko do podmiany.")

        if placeholder_text:
            lines = [line for line in lines if line["text"].strip() == placeholder_text.strip()]
            if not lines:
                raise PlacecardError(f"Nie znaleziono tekstu w szablonie: {placeholder_text.strip()}")

        return [_line_group_to_field(group, page) for group in _group_text_lines(lines)]
    finally:
        doc.close()


def resolve_font_path(font_name: str = "", explicit_font_path: str | Path | None = None) -> Path:
    if explicit_font_path:
        path = Path(explicit_font_path)
        if path.exists():
            return path
        raise PlacecardError(f"Nie znaleziono fontu: {path}")

    normalized = _normalize_font_name(font_name)
    candidates: list[Path] = []

    font_roots = [
        Path("C:/Windows/Fonts"),
        Path.home() / "AppData/Local/Microsoft/Windows/Fonts",
    ]
    extensions = (".otf", ".ttf", ".ttc")

    if normalized:
        for root in font_roots:
            if not root.exists():
                continue
            for path in root.iterdir():
                if path.suffix.lower() not in extensions:
                    continue
                if _normalize_font_name(path.stem) == normalized:
                    candidates.append(path)

    fallback_names = [
        "AGaramondPro-Italic",
        "AGaramondPro-Regular",
        "GARAIT",
        "GARA",
        "timesi",
        "times",
    ]
    for root in font_roots:
        for name in fallback_names:
            for ext in extensions:
                candidates.append(root / f"{name}{ext}")

    for path in candidates:
        if path.exists():
            return path

    raise PlacecardError(
        "Nie znaleziono fontu ze wzoru. Wybierz recznie plik OTF/TTF z tym krojem."
    )


def create_placecards_pdf_file(
    template_pdf: str | Path,
    people: str | Iterable[str],
    output_pdf: str | Path,
    *,
    font_path: str | Path | None = None,
    placeholder_text: str | None = None,
    template_fields: Iterable[TemplateTextField | dict] | None = None,
    settings: PlacecardSettings | None = None,
    progress: ProgressCallback | None = None,
) -> Path:
    pdf_bytes = create_placecards_pdf_bytes(
        template_pdf,
        people,
        font_path=font_path,
        placeholder_text=placeholder_text,
        template_fields=template_fields,
        settings=settings,
        progress=progress,
    )
    output_path = Path(output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(pdf_bytes)
    return output_path


def create_placecards_pdf_bytes(
    template_pdf: str | Path,
    people: str | Iterable[str],
    *,
    font_path: str | Path | None = None,
    placeholder_text: str | None = None,
    template_fields: Iterable[TemplateTextField | dict] | None = None,
    settings: PlacecardSettings | None = None,
    progress: ProgressCallback | None = None,
) -> bytes:
    settings = settings or PlacecardSettings()
    settings.validate()

    names = normalize_people(people)
    if not names:
        raise PlacecardError("Lista osob jest pusta.")

    template_path = Path(template_pdf)
    fields = _coerce_template_fields(template_fields, template_path, placeholder_text)
    font_file = resolve_font_path(fields[0].font_name, explicit_font_path=font_path)
    raster_font = _RasterFont(font_file, settings.raster_dpi)

    src = _open_pdf(template_path)
    out = fitz.open()
    try:
        _copy_metadata(src, out)
        for index, name in enumerate(names, start=1):
            out.insert_pdf(src, from_page=0, to_page=0)
            page = out[-1]
            _remove_template_texts(page, fields, settings)
            for field in fields:
                _insert_name(page, name, field, settings, raster_font, _text_area_width(field, settings))
            if progress:
                progress(index, len(names))

        return out.write(garbage=4, deflate=True)
    finally:
        out.close()
        src.close()


def _open_pdf(path: Path) -> fitz.Document:
    try:
        doc = fitz.open(path)
    except Exception as exc:
        raise PlacecardError(f"Nie udalo sie otworzyc PDF: {exc}") from exc

    if doc.needs_pass:
        doc.close()
        raise PlacecardError("PDF jest zabezpieczony haslem.")
    if doc.page_count < 1:
        doc.close()
        raise PlacecardError("PDF nie ma stron.")
    return doc


def _coerce_template_fields(
    template_fields: Iterable[TemplateTextField | dict] | None,
    template_path: Path,
    placeholder_text: str | None,
) -> list[TemplateTextField]:
    if template_fields is None:
        return inspect_template_fields(template_path, placeholder_text=placeholder_text)

    doc = _open_pdf(template_path)
    try:
        page = doc[0]
        fields: list[TemplateTextField] = []
        for field in template_fields:
            if isinstance(field, TemplateTextStyle):
                fields.append(field)
                continue

            bbox = tuple(float(value) for value in field["bbox"])
            erase_bbox = field.get("erase_bbox")
            fields.append(
                TemplateTextField(
                    text=str(field.get("text", "Jan Nowak")),
                    font_name=str(field.get("font_name", "")),
                    font_size_pt=float(field.get("font_size_pt", 24.0)),
                    color_rgb=tuple(field.get("color_rgb", (0, 0, 0))),
                    bbox=bbox,
                    page_width_pt=float(page.rect.width),
                    page_height_pt=float(page.rect.height),
                    rotation=int(field.get("rotation", 0)),
                    max_width_pt=field.get("max_width_pt"),
                    erase_bbox=tuple(float(value) for value in erase_bbox) if erase_bbox else None,
                    remove_graphics=bool(field.get("remove_graphics", False)),
                    underline_mode=field.get("underline_mode"),
                    force_two_lines=bool(field.get("force_two_lines", False)),
                )
            )
        if not fields:
            raise PlacecardError("Szablon nie ma zdefiniowanego pola tekstowego.")
        return fields
    finally:
        doc.close()


def _text_lines(page: fitz.Page) -> list[dict]:
    lines_out: list[dict] = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            spans = [span for span in line.get("spans", []) if str(span.get("text", "")).strip()]
            if not spans:
                continue
            text = "".join(str(span.get("text", "")) for span in spans).strip()
            if text:
                lines_out.append(
                    {
                        "text": text,
                        "dir": tuple(line.get("dir", (1.0, 0.0))),
                        "bbox": tuple(float(value) for value in line.get("bbox")),
                        "spans": spans,
                    }
                )
    return lines_out


def _group_text_lines(lines: list[dict]) -> list[list[dict]]:
    if len(lines) == 2 and _should_group_two_line_placeholder(lines[0], lines[1]):
        return [lines]
    return [[line] for line in lines]


def _should_group_two_line_placeholder(first: dict, second: dict) -> bool:
    if tuple(first["dir"]) != tuple(second["dir"]):
        return False
    first_rect = fitz.Rect(first["bbox"])
    second_rect = fitz.Rect(second["bbox"])
    x_distance = abs(first_rect.tl.x + first_rect.width / 2.0 - (second_rect.tl.x + second_rect.width / 2.0))
    vertical_gap = second_rect.y0 - first_rect.y1
    max_height = max(first_rect.height, second_rect.height)
    return x_distance < 70.0 and vertical_gap < max_height * 0.35


def _line_group_to_field(group: list[dict], page: fitz.Page) -> TemplateTextField:
    first = group[0]
    first_span = max(
        (span for line in group for span in line["spans"]),
        key=lambda span: float(span.get("size", 0.0)),
    )
    bbox = fitz.Rect(group[0]["bbox"])
    for line in group[1:]:
        bbox |= fitz.Rect(line["bbox"])
    direction = tuple(first.get("dir", (1.0, 0.0)))
    rotation = 180 if direction[0] < -0.5 else 0
    return TemplateTextField(
        text=" ".join(line["text"] for line in group),
        font_name=str(first_span.get("font", "")),
        font_size_pt=float(first_span.get("size", 24.0)),
        color_rgb=_color_int_to_rgb(int(first_span.get("color", 0))),
        bbox=tuple(float(value) for value in bbox),
        page_width_pt=float(page.rect.width),
        page_height_pt=float(page.rect.height),
        rotation=rotation,
        force_two_lines=len(group) > 1,
    )


def _copy_metadata(src: fitz.Document, dst: fitz.Document) -> None:
    metadata = src.metadata or {}
    cleaned = {key: value for key, value in metadata.items() if value}
    if cleaned:
        try:
            dst.set_metadata(cleaned)
        except Exception:
            pass


def _remove_template_texts(page: fitz.Page, fields: list[TemplateTextField], settings: PlacecardSettings) -> None:
    needs_apply = False
    remove_graphics = False
    for field in fields:
        padding = settings.erase_padding_pt
        rect = fitz.Rect(field.erase_bbox or field.bbox) + (-padding, -padding, padding, padding)
        page.add_redact_annot(rect, fill=(1, 1, 1) if field.remove_graphics else None, cross_out=False)
        needs_apply = True
        remove_graphics = remove_graphics or field.remove_graphics
    if needs_apply:
        page.apply_redactions(images=0, graphics=1 if remove_graphics else 0, text=0)


def _insert_name(
    page: fitz.Page,
    name: str,
    style: TemplateTextField,
    settings: PlacecardSettings,
    raster_font: _RasterFont,
    max_width_pt: float,
) -> None:
    lines, font_size = _layout_name(
        name,
        style.font_size_pt,
        max_width_pt,
        settings,
        raster_font,
        force_two_lines=style.force_two_lines,
    )
    if style.underline_mode == "o05" and len(lines) > 1:
        font_size = min(font_size, 28.0)
    image = _render_name_image(lines, font_size, style.color_rgb, settings, raster_font, style.underline_mode)
    max_height_pt = fitz.Rect(style.bbox).height * 0.86
    while image.height * 72.0 / settings.raster_dpi > max_height_pt and font_size > settings.min_font_size_pt:
        font_size -= 0.5
        image = _render_name_image(lines, font_size, style.color_rgb, settings, raster_font, style.underline_mode)
    if style.rotation == 180:
        image = image.rotate(180, expand=True)
    image_bytes = _image_to_png_bytes(image)
    width_pt = image.width * 72.0 / settings.raster_dpi
    height_pt = image.height * 72.0 / settings.raster_dpi
    rect = fitz.Rect(
        style.center_x - width_pt / 2.0,
        style.center_y - height_pt / 2.0,
        style.center_x + width_pt / 2.0,
        style.center_y + height_pt / 2.0,
    )
    page.insert_image(rect, stream=image_bytes, overlay=True)


def _layout_name(
    name: str,
    base_size_pt: float,
    max_width_pt: float,
    settings: PlacecardSettings,
    raster_font: _RasterFont,
    force_two_lines: bool = False,
) -> tuple[list[str], float]:
    if not force_two_lines and raster_font.text_length_pt(name, base_size_pt) <= max_width_pt:
        return [name], base_size_pt

    words = name.split()
    if len(words) < 2:
        lines = [name]
    else:
        lines = _best_two_line_split(words, base_size_pt, raster_font)

    size = base_size_pt
    while size > settings.min_font_size_pt:
        if max(raster_font.text_length_pt(line, size) for line in lines) <= max_width_pt:
            break
        size -= 0.5

    return lines, max(size, settings.min_font_size_pt)


def _best_two_line_split(words: list[str], size_pt: float, raster_font: _RasterFont) -> list[str]:
    best_score: float | None = None
    best_lines: list[str] | None = None

    for split_at in range(1, len(words)):
        lines = [" ".join(words[:split_at]), " ".join(words[split_at:])]
        widths = [raster_font.text_length_pt(line, size_pt) for line in lines]
        score = max(widths) + abs(widths[0] - widths[1]) * 0.15
        if best_score is None or score < best_score:
            best_score = score
            best_lines = lines

    return best_lines or [" ".join(words)]


def _render_name_image(
    lines: list[str],
    size_pt: float,
    color_rgb: tuple[int, int, int],
    settings: PlacecardSettings,
    raster_font: _RasterFont,
    underline_mode: str | None = None,
) -> Image.Image:
    if underline_mode == "o05":
        return _render_o05_name_image(lines, size_pt, color_rgb, settings, raster_font)

    font = raster_font.get(size_pt)
    draw = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    advances = [float(draw.textlength(line, font=font)) for line in lines]
    ascent, descent = font.getmetrics()
    size_px = max(1, int(round(size_pt * settings.raster_dpi / 72.0)))
    line_gap_px = max(1, int(round(size_px * settings.line_gap_factor)))
    pad_px = max(12, int(round(size_px * 0.25)))
    content_width = max(advances) if advances else 1.0
    width = int(round(content_width + pad_px * 2))
    height = int(round(ascent + descent + (len(lines) - 1) * line_gap_px + pad_px * 2))

    image = Image.new("RGBA", (max(1, width), max(1, height)), (255, 255, 255, 0))
    image_draw = ImageDraw.Draw(image)
    fill = (*color_rgb, 255)

    for index, line in enumerate(lines):
        advance = advances[index]
        x = pad_px + (content_width - advance) / 2.0
        y = pad_px + ascent + index * line_gap_px
        image_draw.text((x, y), line, font=font, fill=fill, anchor="ls")

    bbox = image.getbbox()
    if not bbox:
        raise PlacecardError("Nie udalo sie wyrenderowac tekstu.")

    crop_pad = max(2, int(round(2.0 * settings.raster_dpi / 72.0)))
    crop = (
        max(0, bbox[0] - crop_pad),
        max(0, bbox[1] - crop_pad),
        min(image.width, bbox[2] + crop_pad),
        min(image.height, bbox[3] + crop_pad),
    )
    return image.crop(crop)


def _render_o05_name_image(
    lines: list[str],
    size_pt: float,
    color_rgb: tuple[int, int, int],
    settings: PlacecardSettings,
    raster_font: _RasterFont,
) -> Image.Image:
    font = raster_font.get(size_pt)
    helper = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    size_px = max(1, int(round(size_pt * settings.raster_dpi / 72.0)))
    pad_x = max(18, int(round(size_px * 0.28)))
    pad_y = max(18, int(round(size_px * 0.22)))
    ascent, descent = font.getmetrics()
    advances = [float(helper.textlength(line, font=font)) for line in lines]
    content_width = max(max(advances, default=1.0), _pt_to_px(94.0, settings.raster_dpi))

    if len(lines) == 1:
        rel_bbox = helper.textbbox((0, 0), lines[0], font=font, anchor="ls")
        first_baseline = pad_y - rel_bbox[1]
        line_y = first_baseline + rel_bbox[3] + _pt_to_px(1.5, settings.raster_dpi)
        height = line_y + _pt_to_px(7.0, settings.raster_dpi) + pad_y
        baselines = [first_baseline]
    else:
        first_rel = helper.textbbox((0, 0), lines[0], font=font, anchor="ls")
        second_rel = helper.textbbox((0, 0), lines[1], font=font, anchor="ls")
        first_baseline = pad_y - first_rel[1]
        line_y = first_baseline + first_rel[3] + _pt_to_px(3.0, settings.raster_dpi)
        second_baseline = line_y + _pt_to_px(4.5, settings.raster_dpi) - second_rel[1]
        height = second_baseline + second_rel[3] + pad_y
        baselines = [first_baseline, second_baseline]

    width = int(round(content_width + pad_x * 2))
    image = Image.new("RGBA", (max(1, width), max(1, height)), (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    fill = (*color_rgb, 255)

    for index, line in enumerate(lines):
        advance = advances[index]
        x = pad_x + (content_width - advance) / 2.0
        draw.text((x, baselines[index]), line, font=font, fill=fill, anchor="ls")

    _draw_o05_underline(draw, width / 2.0, float(line_y), color_rgb, settings.raster_dpi)
    bbox = image.getbbox()
    if not bbox:
        raise PlacecardError("Nie udalo sie wyrenderowac tekstu.")

    crop_pad = max(2, _pt_to_px(2.0, settings.raster_dpi))
    crop = (
        max(0, bbox[0] - crop_pad),
        max(0, bbox[1] - crop_pad),
        min(image.width, bbox[2] + crop_pad),
        min(image.height, bbox[3] + crop_pad),
    )
    return image.crop(crop)


def _draw_o05_underline(
    draw: ImageDraw.ImageDraw,
    center_x: float,
    y: float,
    color_rgb: tuple[int, int, int],
    dpi: int,
) -> None:
    color = (*color_rgb, 255)
    half_length = _pt_to_px(45.0, dpi)
    gap = _pt_to_px(3.2, dpi)
    stroke = max(2, _pt_to_px(0.55, dpi))
    diamond = _pt_to_px(2.3, dpi)
    left = center_x - half_length
    right = center_x + half_length
    draw.line((left, y, center_x - gap, y), fill=color, width=stroke)
    draw.line((center_x + gap, y, right, y), fill=color, width=stroke)
    points = [
        (center_x, y - diamond),
        (center_x + diamond, y),
        (center_x, y + diamond),
        (center_x - diamond, y),
    ]
    draw.line(points + [points[0]], fill=color, width=stroke)


def _pt_to_px(value_pt: float, dpi: int) -> int:
    return max(1, int(round(value_pt * dpi / 72.0)))


def _image_to_png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _text_area_width(style: TemplateTextStyle, settings: PlacecardSettings) -> float:
    if style.max_width_pt:
        return style.max_width_pt
    left_space = style.center_x - settings.horizontal_margin_pt
    right_space = style.page_width_pt - style.center_x - settings.horizontal_margin_pt
    return max(1.0, 2.0 * min(left_space, right_space))


def _color_int_to_rgb(color: int) -> tuple[int, int, int]:
    return ((color >> 16) & 255, (color >> 8) & 255, color & 255)


def _normalize_font_name(name: str) -> str:
    name = name.split("+")[-1]
    return re.sub(r"[^a-z0-9]", "", name.lower())
