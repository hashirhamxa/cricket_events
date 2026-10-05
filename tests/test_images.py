"""Tests for image validation and conversion."""

import io
from PIL import Image
import pytest
from src.images import TeamImageManager


def test_valid_image_conversion():
    # Create valid synthetic RGB image
    img = Image.new("RGB", (100, 100), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    mgr = TeamImageManager()
    png_bytes = mgr.validate_and_convert_bytes(jpeg_bytes)

    assert png_bytes is not None
    assert len(png_bytes) > 0
    # Verify resulting output is readable PNG
    out_img = Image.open(io.BytesIO(png_bytes))
    assert out_img.format == "PNG"
    assert out_img.size == (100, 100)


def test_reject_html_error_payload():
    html_error = b"<html><body><h1>503 Service Unavailable</h1></body></html>"
    mgr = TeamImageManager()
    assert mgr.validate_and_convert_bytes(html_error) is None


def test_reject_tiny_placeholder():
    # 1x1 GIF
    img = Image.new("P", (1, 1))
    buf = io.BytesIO()
    img.save(buf, format="GIF")
    gif_bytes = buf.getvalue()

    mgr = TeamImageManager()
    assert mgr.validate_and_convert_bytes(gif_bytes) is None


def test_reject_corrupted_bytes():
    corrupted = b"this is completely invalid garbage data not an image"
    mgr = TeamImageManager()
    assert mgr.validate_and_convert_bytes(corrupted) is None
