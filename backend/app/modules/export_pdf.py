import os
from typing import Optional

import fitz
from PIL import Image, ImageFont

from app import config
from app.models.document import PageAnalysis
from app.models.edit import Edit, EditTargetBBox, TextConfig
from app.modules import ocr, page_analysis
from app.modules.background_cover import create_cover_patch, sample_dominant_background
from app.modules.coordinates import pdf_bbox_to_image_bbox, pdf_points_to_image_pixels
from app.modules.document_intake import get_document
from app.modules.edit_layer import list_edits
from app.modules.font_registry import resolve_font_path
from app.modules.page_rendering import get_page_dimensions, get_page_image, render_page
from app.modules import page_crop


def _document_pdf_path(document_id: str) -> str:
    return os.path.join(config.DATA_DIR, document_id, "original.pdf")


def _edit_to_image_space(
    edit: Edit,
    *,
    page_width: float,
    page_height: float,
    image_width: float,
    image_height: float,
) -> Edit:
    image_bbox = pdf_bbox_to_image_bbox(
        edit.target_bbox,
        page_width=page_width,
        page_height=page_height,
        image_width=image_width,
        image_height=image_height,
    )
    image_text = TextConfig(
        value=edit.text.value,
        x=pdf_points_to_image_pixels(edit.text.x, page_width, image_width),
        y=pdf_points_to_image_pixels(edit.text.y, page_height, image_height),
        font_size=pdf_points_to_image_pixels(edit.text.font_size, page_height, image_height),
        font_id=edit.text.font_id,
        font_family=edit.text.font_family,
        color=edit.text.color,
        bold=edit.text.bold,
        italic=edit.text.italic,
    )
    return edit.model_copy(
        update={
            "target_bbox": EditTargetBBox(**image_bbox.model_dump()),
            "text": image_text,
        }
    )


def _parse_hex_color(value: str, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    color = (value or "").strip().lstrip("#")
    if len(color) != 6:
        return fallback
    try:
        return tuple(int(color[i : i + 2], 16) / 255 for i in (0, 2, 4))
    except ValueError:
        return fallback


def _rect_from_bbox(bbox: EditTargetBBox, padding: float = 0) -> fitz.Rect:
    return fitz.Rect(
        bbox.x - padding,
        bbox.y - padding,
        bbox.x + bbox.w + padding,
        bbox.y + bbox.h + padding,
    )


def _apply_page_crop(page: fitz.Page, crop: Optional[EditTargetBBox]) -> None:
    if not crop:
        return
    rect = fitz.Rect(crop.x, crop.y, crop.x + crop.w, crop.y + crop.h)
    if not rect.is_empty:
        page.set_cropbox(rect)


def _sample_pdf_background(
    document_id: str,
    page_number: int,
    bbox: EditTargetBBox,
    *,
    page_width: float,
    page_height: float,
) -> tuple[float, float, float]:
    render_page(document_id, page_number, dpi=config.PREVIEW_DPI)
    image = Image.open(get_page_image(document_id, page_number)).convert("RGB")
    image_bbox = pdf_bbox_to_image_bbox(
        bbox,
        page_width=page_width,
        page_height=page_height,
        image_width=image.width,
        image_height=image.height,
    )
    sampled = sample_dominant_background(image, image_bbox)
    return tuple(channel / 255 for channel in sampled)


def _cover_color(
    document_id: str,
    page_number: int,
    edit: Edit,
    *,
    page_width: float,
    page_height: float,
) -> tuple[float, float, float]:
    if edit.cover.method == "sampled_background":
        return _sample_pdf_background(
            document_id,
            page_number,
            edit.target_bbox,
            page_width=page_width,
            page_height=page_height,
        )
    return (1, 1, 1)


def _insert_pdf_text(page: fitz.Page, edit: Edit) -> None:
    if not edit.text.value:
        return

    font_path = resolve_font_path(
        font_id=edit.text.font_id,
        font_family=edit.text.font_family,
    )
    color = _parse_hex_color(edit.text.color, (0.067, 0.067, 0.067))
    x = edit.text.x or edit.target_bbox.x
    y = edit.text.y or edit.target_bbox.y
    right = max(x + edit.target_bbox.w, x + 1)
    bottom = max(y + edit.target_bbox.h, y + 1)
    text_rect = fitz.Rect(x, y, right, bottom)
    font_size = _fit_font_size(
        edit.text.value,
        font_path=font_path,
        requested_size=max(float(edit.text.font_size), 1.0),
        max_width=max(text_rect.width, 1),
        max_height=max(text_rect.height, 1),
    )
    kwargs = {
        "fontsize": font_size,
        "color": color,
        "overlay": True,
    }
    if font_path:
        kwargs["fontname"] = "custom"
        kwargs["fontfile"] = font_path
    else:
        kwargs["fontname"] = "helv"

    if "\n" not in edit.text.value:
        baseline = _single_line_baseline(text_rect, font_size)
        page.insert_text((x, baseline), edit.text.value, **kwargs)
        return

    for attempt in range(6):
        kwargs["fontsize"] = max(1.0, font_size * (0.9**attempt))
        overflow = page.insert_textbox(
            text_rect,
            edit.text.value,
            align=fitz.TEXT_ALIGN_LEFT,
            **kwargs,
        )
        if overflow >= 0:
            return

    kwargs["fontsize"] = max(1.0, font_size * 0.5)
    page.insert_text((x, _single_line_baseline(text_rect, kwargs["fontsize"])), edit.text.value, **kwargs)


def _single_line_baseline(rect: fitz.Rect, font_size: float) -> float:
    usable_height = max(rect.height, font_size)
    return rect.y0 + max(font_size, (usable_height + font_size * 0.72) / 2)


def _fit_font_size(
    text: str,
    *,
    font_path: Optional[str],
    requested_size: float,
    max_width: float,
    max_height: float,
) -> float:
    if not text.strip():
        return requested_size

    min_size = 4.0
    size = max(requested_size, min_size)
    lines = text.splitlines() or [text]
    measured_width, measured_height = _measure_text(lines, size, font_path)
    if measured_width <= 0 or measured_height <= 0:
        return size

    width_ratio = max_width / measured_width
    height_ratio = max_height / measured_height
    fit_ratio = min(1.0, width_ratio, height_ratio)
    return max(min_size, size * fit_ratio * 0.96)


def _measure_text(lines: list[str], font_size: float, font_path: Optional[str]) -> tuple[float, float]:
    try:
        if font_path:
            font = ImageFont.truetype(font_path, max(1, int(round(font_size))))
            widths = []
            heights = []
            for line in lines:
                bbox = font.getbbox(line or " ")
                widths.append(max(0, bbox[2] - bbox[0]))
                heights.append(max(1, bbox[3] - bbox[1]))
            return float(max(widths, default=0)), float(sum(heights) * 1.15)
    except Exception:
        pass

    longest = max(lines, key=len, default="")
    width = len(longest) * font_size * 0.56
    height = len(lines) * font_size * 1.15
    return width, height


def _apply_pdf_edits(
    page: fitz.Page,
    edits: list[Edit],
    *,
    document_id: str,
    page_number: int,
    page_width: float,
    page_height: float,
) -> None:
    has_redactions = False
    for edit in edits:
        if not edit.cover.enabled:
            continue
        fill = _cover_color(
            document_id,
            page_number,
            edit,
            page_width=page_width,
            page_height=page_height,
        )
        page.add_redact_annot(
            _rect_from_bbox(edit.target_bbox, min(float(edit.cover.padding), 0.75)),
            fill=fill,
            cross_out=False,
        )
        has_redactions = True

    if has_redactions:
        page.apply_redactions(
            images=fitz.PDF_REDACT_IMAGE_NONE,
            graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
            text=fitz.PDF_REDACT_TEXT_REMOVE,
        )

    for edit in edits:
        _insert_pdf_text(page, edit)


def _add_invisible_ocr_text(page: fitz.Page, document_id: str, page_number: int) -> None:
    result = ocr.get_ocr_result(document_id, page_number)
    if not result:
        return

    for block in result.blocks:
        rect = fitz.Rect(
            block.bbox.x,
            block.bbox.y,
            block.bbox.x + block.bbox.w,
            block.bbox.y + block.bbox.h,
        )
        if rect.is_empty or not block.text.strip():
            continue
        page.insert_text(
            (rect.x0, rect.y0 + max(block.bbox.h * 0.8, 1)),
            block.text,
            fontsize=max(block.bbox.h * 0.8, 1),
            fontname="helv",
            fill_opacity=0,
            overlay=True,
        )


def _render_raster_page(
    pdf_writer: fitz.Document,
    document_id: str,
    page_number: int,
    edits: list[Edit],
    *,
    add_ocr_layer: bool,
) -> None:
    dim_w, dim_h = get_page_dimensions(document_id, page_number)

    render_page(document_id, page_number, dpi=config.EXPORT_DPI)
    img = Image.open(get_page_image(document_id, page_number)).convert("RGB")
    image_w, image_h = img.size

    for edit in edits:
        image_edit = _edit_to_image_space(
            edit,
            page_width=dim_w,
            page_height=dim_h,
            image_width=image_w,
            image_height=image_h,
        )
        if edit.cover.enabled:
            img = create_cover_patch(
                img,
                image_edit.target_bbox,
                method=edit.cover.method,
            )

    out_dir = os.path.join(config.DATA_DIR, document_id, "export")
    temp_png = os.path.join(out_dir, f"page_{page_number:03d}.png")
    img.save(temp_png, "PNG")

    page = pdf_writer.new_page(width=dim_w, height=dim_h)
    page.insert_image(page.rect, filename=temp_png)

    if add_ocr_layer:
        _add_invisible_ocr_text(page, document_id, page_number)

    for edit in edits:
        _insert_pdf_text(page, edit)

    crop = page_crop.get_crop_box(document_id, page_number)
    if crop:
        _apply_page_crop(page, EditTargetBBox(x=crop.x, y=crop.y, w=crop.w, h=crop.h))


def _page_mode(analyses: dict[int, PageAnalysis], page_number: int) -> str:
    analysis = analyses.get(page_number)
    return analysis.mode if analysis else "scanned"


def export_document(document_id: str) -> str:
    meta = get_document(document_id)
    if not meta:
        raise ValueError(f"Document {document_id} not found")

    out_dir = os.path.join(config.DATA_DIR, document_id, "export")
    os.makedirs(out_dir, exist_ok=True)
    out_pdf = os.path.join(out_dir, "edited.pdf")

    source_pdf = fitz.open(_document_pdf_path(document_id))
    pdf_writer = fitz.open()
    analyses = {
        analysis.page_number: analysis
        for analysis in page_analysis.load_page_analysis(document_id)
    }

    try:
        for page_num in range(1, meta.page_count + 1):
            edits = list_edits(document_id, page_num)
            mode = _page_mode(analyses, page_num)

            if mode == "scanned":
                _render_raster_page(
                    pdf_writer,
                    document_id,
                    page_num,
                    edits,
                    add_ocr_layer=True,
                )
                continue

            try:
                pdf_writer.insert_pdf(source_pdf, from_page=page_num - 1, to_page=page_num - 1)
                page = pdf_writer[-1]
                dim_w, dim_h = get_page_dimensions(document_id, page_num)
                _apply_pdf_edits(
                    page,
                    edits,
                    document_id=document_id,
                    page_number=page_num,
                    page_width=dim_w,
                    page_height=dim_h,
                )
                crop = page_crop.get_crop_box(document_id, page_num)
                if crop:
                    _apply_page_crop(page, EditTargetBBox(x=crop.x, y=crop.y, w=crop.w, h=crop.h))
            except Exception:
                if pdf_writer.page_count >= page_num:
                    pdf_writer.delete_page(pdf_writer.page_count - 1)
                _render_raster_page(
                    pdf_writer,
                    document_id,
                    page_num,
                    edits,
                    add_ocr_layer=mode == "hybrid",
                )

        pdf_writer.save(out_pdf)
    finally:
        pdf_writer.close()
        source_pdf.close()

    return out_pdf
