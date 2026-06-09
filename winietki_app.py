from __future__ import annotations

import io
import os
import queue
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk

import fitz
from PIL import Image, ImageTk

from cr_placecards import PlacecardError, create_placecards_pdf_bytes, normalize_people


APP_NAME = "CR Winietki"
WHITE = "#ffffff"
TEXT = "#090909"
MUTED = "#686868"
BORDER = "#d8d8d8"
BLACK = "#000000"
HOVER = "#202020"
SOFT = "#f7f7f7"


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


@dataclass(frozen=True)
class WorkerEvent:
    kind: str
    message: str = ""
    pdf_bytes: bytes | None = None
    page_count: int = 0


class RoundedButton(tk.Canvas):
    def __init__(
        self,
        parent,
        text: str,
        command,
        width: int,
        height: int,
        bg: str = BLACK,
        fg: str = WHITE,
        radius: int = 10,
        font=("Segoe UI", 12, "bold"),
    ) -> None:
        super().__init__(parent, width=width, height=height, bg=WHITE, highlightthickness=0, bd=0)
        self.command = command
        self.normal_bg = bg
        self.hover_bg = HOVER if bg == BLACK else "#eeeeee"
        self.fg = fg
        self.radius = radius
        self.font = font
        self.text = text
        self.enabled = True
        self.bind("<Button-1>", self._click)
        self.bind("<Enter>", lambda _event: self._draw(self.hover_bg) if self.enabled else None)
        self.bind("<Leave>", lambda _event: self._draw(self.normal_bg) if self.enabled else None)
        self._draw(self.normal_bg)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._draw(self.normal_bg if enabled else "#bdbdbd")

    def set_text(self, text: str) -> None:
        self.text = text
        self._draw(self.normal_bg if self.enabled else "#bdbdbd")

    def _click(self, _event) -> None:
        if self.enabled:
            self.command()

    def _draw(self, fill: str) -> None:
        self.delete("all")
        width = int(self["width"])
        height = int(self["height"])
        radius = self.radius
        self.create_arc(0, 0, radius * 2, radius * 2, start=90, extent=90, fill=fill, outline=fill)
        self.create_arc(width - radius * 2, 0, width, radius * 2, start=0, extent=90, fill=fill, outline=fill)
        self.create_arc(
            width - radius * 2,
            height - radius * 2,
            width,
            height,
            start=270,
            extent=90,
            fill=fill,
            outline=fill,
        )
        self.create_arc(0, height - radius * 2, radius * 2, height, start=180, extent=90, fill=fill, outline=fill)
        self.create_rectangle(radius, 0, width - radius, height, fill=fill, outline=fill)
        self.create_rectangle(0, radius, width, height - radius, fill=fill, outline=fill)
        self.create_text(width / 2, height / 2, text=self.text, fill=self.fg, font=self.font)


class ScrollFrame(tk.Frame):
    def __init__(self, parent: tk.Widget, bg: str = WHITE) -> None:
        super().__init__(parent, bg=bg)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self.canvas.yview)
        self.inner = tk.Frame(self.canvas, bg=bg)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.inner.bind("<Configure>", self._sync_scrollregion)
        self.canvas.bind("<Configure>", self._sync_width)
        self.canvas.bind("<Enter>", lambda _event: self.canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        self.canvas.bind("<Leave>", lambda _event: self.canvas.unbind_all("<MouseWheel>"))
        self.bind("<Destroy>", self._on_destroy)

    def _sync_scrollregion(self, _event=None) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _sync_width(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _on_mousewheel(self, event) -> None:
        if self.winfo_ismapped():
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _on_destroy(self, _event) -> None:
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except tk.TclError:
            pass


class PlacecardApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1120x780")
        self.root.minsize(940, 660)
        self.root.configure(bg=WHITE)

        self.event_queue: queue.Queue[WorkerEvent] = queue.Queue()
        self.worker: threading.Thread | None = None
        self.selected_template: PlacecardTemplate | None = None
        self.generated_pdf: bytes | None = None
        self.people_raw = ""
        self.template_thumbnails: dict[str, ImageTk.PhotoImage] = {}
        self.preview_images: list[ImageTk.PhotoImage] = []
        self.status_var = tk.StringVar(value="")
        self.count_var = tk.StringVar(value="")
        self.generate_button: RoundedButton | None = None

        self._try_set_icon()
        self._show_template_screen()
        self.root.after(100, self._poll_queue)

    def _try_set_icon(self) -> None:
        icon_path = app_resource_path("assets", "autospady.ico")
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except tk.TclError:
                pass

    def _clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def _show_template_screen(self) -> None:
        self._clear()
        self.generated_pdf = None
        self.people_raw = ""
        self.preview_images = []
        page = tk.Frame(self.root, bg=WHITE, padx=34, pady=30)
        page.pack(fill=tk.BOTH, expand=True)

        tk.Label(page, text=APP_NAME, bg=WHITE, fg=TEXT, font=("Segoe UI", 26, "bold")).pack(anchor="w")
        tk.Label(page, text="Wybierz szablon winietki z katalogu.", bg=WHITE, fg=MUTED, font=("Segoe UI", 11)).pack(
            anchor="w", pady=(4, 24)
        )

        scroll = ScrollFrame(page, bg=WHITE)
        scroll.pack(fill=tk.BOTH, expand=True)

        for category in CATEGORY_ORDER:
            templates = [template for template in TEMPLATES if template.category == category]
            if not templates:
                continue
            section = tk.Frame(scroll.inner, bg=WHITE)
            section.pack(fill=tk.X, pady=(0, 20))
            header = tk.Frame(section, bg=WHITE)
            header.pack(fill=tk.X, padx=(0, 0), pady=(0, 8))
            tk.Label(header, text=category, bg=WHITE, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(side=tk.LEFT)
            tk.Label(
                header,
                text=f"{format_money(templates[0].price)} / szt.",
                bg=WHITE,
                fg=MUTED,
                font=("Segoe UI", 11),
            ).pack(side=tk.LEFT, padx=(12, 0), pady=(5, 0))

            grid = tk.Frame(section, bg=WHITE)
            grid.pack(fill=tk.X)
            for index, template in enumerate(templates):
                card = self._template_card(grid, template)
                card.grid(row=index // 5, column=index % 5, padx=10, pady=10, sticky="n")
            for column in range(5):
                grid.grid_columnconfigure(column, weight=1)

    def _template_card(self, parent: tk.Widget, template: PlacecardTemplate) -> tk.Frame:
        frame = tk.Frame(parent, bg=WHITE, bd=1, relief=tk.SOLID, highlightthickness=1, highlightbackground=BORDER)
        frame.configure(cursor="hand2")
        thumbnail = self._template_thumbnail(template)
        image_label = tk.Label(frame, image=thumbnail, bg=WHITE)
        image_label.pack(padx=12, pady=(12, 8))
        tk.Label(frame, text=template.name, bg=WHITE, fg=TEXT, font=("Segoe UI", 13, "bold")).pack()
        tk.Label(frame, text=f"{format_money(template.price)} / szt.", bg=WHITE, fg=MUTED, font=("Segoe UI", 9)).pack(
            pady=(2, 10)
        )

        def choose(_event=None) -> None:
            self.selected_template = template
            self._show_people_screen()

        for widget in (frame, image_label):
            widget.bind("<Button-1>", choose)
        for child in frame.winfo_children():
            child.bind("<Button-1>", choose)
        return frame

    def _template_thumbnail(self, template: PlacecardTemplate) -> ImageTk.PhotoImage:
        if template.key in self.template_thumbnails:
            return self.template_thumbnails[template.key]

        try:
            doc = fitz.open(template_pdf_path(template))
            pix = doc[0].get_pixmap(matrix=fitz.Matrix(0.55, 0.55), alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png")))
            image.thumbnail((150, 170), Image.Resampling.LANCZOS)
            doc.close()
        except Exception:
            image = Image.new("RGB", (150, 170), "white")
        photo = ImageTk.PhotoImage(image)
        self.template_thumbnails[template.key] = photo
        return photo

    def _show_people_screen(self) -> None:
        self._clear()
        template = self._require_template()
        shell = tk.Frame(self.root, bg=WHITE)
        shell.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(shell, bg=WHITE, padx=34, pady=30)
        left.pack(side=tk.LEFT, fill=tk.Y)
        right = tk.Frame(shell, bg=SOFT, padx=24, pady=24)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        tk.Label(left, text=template.name, bg=WHITE, fg=TEXT, font=("Segoe UI", 26, "bold")).pack(anchor="w")
        tk.Label(
            left,
            text=f"{template.category} | {format_money(template.price)} / szt.",
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 11),
        ).pack(anchor="w", pady=(4, 4))
        tk.Label(left, text="Wklej liste osob, jedna osoba w wierszu.", bg=WHITE, fg=MUTED, font=("Segoe UI", 11)).pack(
            anchor="w", pady=(0, 22)
        )

        self.people_text = tk.Text(
            left,
            width=48,
            height=20,
            bd=1,
            relief=tk.SOLID,
            highlightthickness=0,
            font=("Segoe UI", 10),
            wrap=tk.WORD,
        )
        self.people_text.pack(fill=tk.X)
        self.people_text.bind("<KeyRelease>", self._update_count)
        if self.people_raw:
            self.people_text.insert("1.0", self.people_raw)
        self.people_text.focus_set()
        self._update_count()

        footer = tk.Frame(left, bg=WHITE)
        footer.pack(fill=tk.X, pady=(18, 0))
        tk.Label(footer, textvariable=self.count_var, bg=WHITE, fg=MUTED, font=("Segoe UI", 10)).pack(side=tk.LEFT)

        buttons = tk.Frame(left, bg=WHITE)
        buttons.pack(fill=tk.X, pady=(22, 0))
        RoundedButton(buttons, "Szablony", self._show_template_screen, 120, 42, bg="#eeeeee", fg=TEXT).pack(side=tk.LEFT)
        self.generate_button = RoundedButton(buttons, "Akceptuj", self._generate, 140, 42)
        self.generate_button.pack(side=tk.LEFT, padx=(12, 0))

        tk.Label(left, textvariable=self.status_var, bg=WHITE, fg=MUTED, font=("Segoe UI", 10), wraplength=410).pack(
            anchor="w", pady=(18, 0)
        )

        tk.Label(right, text="Wybrany szablon", bg=SOFT, fg=TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        preview = tk.Label(right, image=self._template_thumbnail(template), bg=WHITE, bd=1, relief=tk.SOLID)
        preview.pack(pady=(18, 0), anchor="n")

    def _update_count(self, _event=None) -> None:
        count = len(normalize_people(self.people_text.get("1.0", tk.END)))
        label = "osoba" if count == 1 else "osob"
        if self.selected_template:
            total = self.selected_template.price * count
            self.count_var.set(
                f"{count} {label} | {format_money(self.selected_template.price)} x {count} = {format_money(total)}"
            )
        else:
            self.count_var.set(f"{count} {label}")

    def _generate(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        template = self._require_template()
        names = normalize_people(self.people_text.get("1.0", tk.END))
        if not names:
            messagebox.showerror(APP_NAME, "Wklej liste osob, po jednej osobie w wierszu.")
            return
        self.people_raw = self.people_text.get("1.0", tk.END).strip()

        if self.generate_button:
            self.generate_button.set_enabled(False)
            self.generate_button.set_text("Tworze...")
        self.status_var.set("Start generowania...")

        def run() -> None:
            try:
                pdf = create_placecards_pdf_bytes(
                    template_pdf_path(template),
                    names,
                    font_path=template_font_path(template),
                    template_fields=template.fields or None,
                    progress=lambda done, total: self.event_queue.put(
                        WorkerEvent("progress", f"Generowanie: {done}/{total}")
                    ),
                )
                self.event_queue.put(WorkerEvent("done", "PDF gotowy.", pdf_bytes=pdf, page_count=len(names)))
            except Exception as exc:
                self.event_queue.put(WorkerEvent("error", str(exc)))

        self.worker = threading.Thread(target=run, daemon=True)
        self.worker.start()

    def _poll_queue(self) -> None:
        try:
            while True:
                event = self.event_queue.get_nowait()
                if event.kind == "progress":
                    self.status_var.set(event.message)
                elif event.kind == "done":
                    self.generated_pdf = event.pdf_bytes
                    self.status_var.set(f"Gotowe: {event.page_count} stron.")
                    if self.generate_button:
                        self.generate_button.set_enabled(True)
                        self.generate_button.set_text("Akceptuj")
                    self._show_preview_screen(event.page_count)
                elif event.kind == "error":
                    self.status_var.set("Blad generowania.")
                    if self.generate_button:
                        self.generate_button.set_enabled(True)
                        self.generate_button.set_text("Akceptuj")
                    messagebox.showerror(APP_NAME, event.message)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _show_preview_screen(self, page_count: int) -> None:
        self._clear()
        template = self._require_template()
        page = tk.Frame(self.root, bg=WHITE, padx=26, pady=24)
        page.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(page, bg=WHITE)
        header.pack(fill=tk.X)
        tk.Label(header, text=f"Podglad: {template.name}", bg=WHITE, fg=TEXT, font=("Segoe UI", 22, "bold")).pack(
            side=tk.LEFT
        )
        total = template.price * page_count
        tk.Label(
            header,
            text=f"{page_count} stron | {format_money(template.price)} x {page_count} = {format_money(total)}",
            bg=WHITE,
            fg=MUTED,
            font=("Segoe UI", 11),
        ).pack(side=tk.LEFT, padx=(12, 0), pady=(6, 0))

        buttons = tk.Frame(header, bg=WHITE)
        buttons.pack(side=tk.RIGHT)
        RoundedButton(buttons, "Wroc", self._show_people_screen, 105, 40, bg="#eeeeee", fg=TEXT).pack(side=tk.LEFT)
        RoundedButton(buttons, "Zapisz PDF", self._save_pdf, 135, 40).pack(side=tk.LEFT, padx=(10, 0))

        scroll = ScrollFrame(page, bg=SOFT)
        scroll.pack(fill=tk.BOTH, expand=True, pady=(18, 0))
        self._fill_preview_pages(scroll.inner)

    def _fill_preview_pages(self, parent: tk.Widget) -> None:
        self.preview_images = []
        if not self.generated_pdf:
            return

        try:
            doc = fitz.open(stream=self.generated_pdf, filetype="pdf")
            columns = 3
            for index in range(doc.page_count):
                pix = doc[index].get_pixmap(matrix=fitz.Matrix(1.15, 1.15), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                image.thumbnail((250, 280), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(image)
                self.preview_images.append(photo)

                cell = tk.Frame(parent, bg=SOFT, padx=14, pady=14)
                cell.grid(row=index // columns, column=index % columns, sticky="n")
                tk.Label(cell, image=photo, bg=WHITE, bd=1, relief=tk.SOLID).pack()
                tk.Label(cell, text=f"Strona {index + 1}", bg=SOFT, fg=MUTED, font=("Segoe UI", 10)).pack(pady=(8, 0))

            for column in range(columns):
                parent.grid_columnconfigure(column, weight=1)
            doc.close()
        except Exception as exc:
            tk.Label(parent, text=f"Nie udalo sie pokazac podgladu: {exc}", bg=SOFT, fg=MUTED).pack(pady=30)

    def _save_pdf(self) -> None:
        if not self.generated_pdf:
            return
        template = self._require_template()
        path = filedialog.asksaveasfilename(
            title="Zapisz PDF z winietkami",
            initialdir=str(Path.home() / "Desktop"),
            initialfile=f"winietki_{template.name}.pdf",
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return
        output = Path(path)
        output.write_bytes(self.generated_pdf)
        try:
            os.startfile(str(output.parent))
        except Exception:
            pass

    def _require_template(self) -> PlacecardTemplate:
        if self.selected_template is None:
            raise PlacecardError("Nie wybrano szablonu.")
        return self.selected_template


def app_resource_path(*parts: str) -> Path:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base.joinpath(*parts)


def template_pdf_path(template: PlacecardTemplate) -> Path:
    return app_resource_path("assets", "placecard_templates", template.pdf_file)


def template_font_path(template: PlacecardTemplate) -> Path:
    return app_resource_path("assets", "placecard_fonts", template.font_file)


def format_money(value: float) -> str:
    return f"{value:.2f}".replace(".", ",") + " zl"


def main() -> None:
    root = tk.Tk()
    PlacecardApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
