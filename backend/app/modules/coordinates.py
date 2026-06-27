from typing import Union

from app.models.edit import EditTargetBBox
from app.models.ocr import OCRBBox

BBoxModel = Union[OCRBBox, EditTargetBBox]


def image_pixels_to_pdf_points(value: float, image_extent: float, page_extent: float) -> float:
    if image_extent == 0:
        raise ValueError("Image extent must be non-zero")
    return value * page_extent / image_extent


def pdf_points_to_image_pixels(value: float, page_extent: float, image_extent: float) -> float:
    if page_extent == 0:
        raise ValueError("Page extent must be non-zero")
    return value * image_extent / page_extent


def image_bbox_to_pdf_bbox(
    bbox: BBoxModel,
    *,
    image_width: float,
    image_height: float,
    page_width: float,
    page_height: float,
) -> OCRBBox:
    return OCRBBox(
        x=image_pixels_to_pdf_points(bbox.x, image_width, page_width),
        y=image_pixels_to_pdf_points(bbox.y, image_height, page_height),
        w=image_pixels_to_pdf_points(bbox.w, image_width, page_width),
        h=image_pixels_to_pdf_points(bbox.h, image_height, page_height),
    )


def pdf_bbox_to_image_bbox(
    bbox: BBoxModel,
    *,
    page_width: float,
    page_height: float,
    image_width: float,
    image_height: float,
) -> EditTargetBBox:
    return EditTargetBBox(
        x=pdf_points_to_image_pixels(bbox.x, page_width, image_width),
        y=pdf_points_to_image_pixels(bbox.y, page_height, image_height),
        w=pdf_points_to_image_pixels(bbox.w, page_width, image_width),
        h=pdf_points_to_image_pixels(bbox.h, page_height, image_height),
    )
