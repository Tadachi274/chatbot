from pathlib import Path

from .config import DEFAULT_PAUSE_DURATION, LANE_BY_ID, SPEAKER_CUSTOMER, SPEAKER_STAFF


A4_WIDTH_MM = 210
A4_HEIGHT_MM = 297
MM_PER_INCH = 25.4
PDF_DPI = 150


def export_conversation_pdf(utterances, output_path):
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:
        raise RuntimeError("PDF出力には Pillow が必要です") from exc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    width = int(A4_WIDTH_MM / MM_PER_INCH * PDF_DPI)
    height = int(A4_HEIGHT_MM / MM_PER_INCH * PDF_DPI)
    margin = int(13 / MM_PER_INCH * PDF_DPI)
    rows = build_export_rows(utterances)

    image, truncated = render_a4_page(rows, width, height, margin, Image, ImageDraw, ImageFont)
    image.save(output_path, "PDF", resolution=PDF_DPI)
    return {"path": output_path, "truncated": truncated, "rows": len(rows)}


def build_export_rows(utterances):
    rows = []
    for utterance in utterances:
        speaker = utterance.get("speaker")
        if speaker == SPEAKER_CUSTOMER:
            text = customer_text(utterance)
            if text:
                rows.append(("客", [text]))
            continue

        if speaker != SPEAKER_STAFF:
            continue

        lines = []
        text = staff_text(utterance)
        if text:
            lines.append(text)
        lines.extend(staff_event_lines(utterance))
        if lines:
            rows.append(("店員", lines))
    return rows


def customer_text(utterance):
    if utterance.get("text"):
        return str(utterance.get("text", "")).strip()
    parts = [
        str(segment.get("text", "")).strip()
        for segment in utterance.get("segments", [])
        if segment.get("type") == "sentence" and str(segment.get("text", "")).strip()
    ]
    return "".join(parts)


def staff_text(utterance):
    parts = [
        str(segment.get("text", "")).strip()
        for segment in utterance.get("segments", [])
        if segment.get("type") == "sentence" and str(segment.get("text", "")).strip()
    ]
    return "".join(parts)


def staff_event_lines(utterance):
    events = sorted(
        [event for event in utterance.get("events", []) if event.get("lane") in LANE_BY_ID],
        key=lambda event: (float(event.get("time", 0.0)), event.get("lane", "")),
    )
    lines = []
    for event in events:
        lane = LANE_BY_ID.get(event.get("lane"), {})
        label = lane.get("label", event.get("lane", "動作"))
        value = str(event.get("value") or lane.get("default", "")).strip()
        if not value:
            continue
        start = float(event.get("time", 0.0))
        duration = float(event.get("duration", DEFAULT_PAUSE_DURATION))
        lines.append(f"{label}: {start:.1f}秒 {value} ({duration:.1f}秒)")
    return lines


def render_a4_page(rows, width, height, margin, Image, ImageDraw, ImageFont):
    font_path = find_japanese_font()
    for font_size in range(24, 11, -1):
        bold_size = font_size + 1
        font = load_font(ImageFont, font_path, font_size)
        bold = load_font(ImageFont, font_path, bold_size)
        layout = make_layout(rows, width - margin * 2, font, bold, Image, ImageDraw)
        if layout["height"] <= height - margin * 2:
            return draw_page(layout, width, height, margin, font, bold, Image, ImageDraw), False

    font = load_font(ImageFont, font_path, 11)
    bold = load_font(ImageFont, font_path, 12)
    layout = make_layout(rows, width - margin * 2, font, bold, Image, ImageDraw)
    return draw_page(layout, width, height, margin, font, bold, Image, ImageDraw, truncate=True), True


def find_japanese_font():
    candidates = [
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
        "/System/Library/Fonts/ヒラギノ丸ゴ ProN W4.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "/System/Library/Fonts/CJKSymbolsFallback.ttc",
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/d7d512f49387f96799ae9271c7fa8f8e9fef05d1.asset/AssetData/BIZ_UDGothic.ttc",
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/54ef167d6c8e99a69a0d41ce252cc5995ba47580.asset/AssetData/YuGothic-Medium.otf",
        "/System/Library/AssetsV2/com_apple_MobileAsset_Font7/a3f9a9e35bdf3babe03b2fd162051306fad439d6.asset/AssetData/Osaka.ttf",
    ]
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
    return None


def load_font(ImageFont, font_path, size):
    if font_path:
        try:
            return ImageFont.truetype(font_path, size)
        except OSError:
            pass
    return ImageFont.load_default()


def make_layout(rows, content_width, font, bold, Image, ImageDraw):
    scratch = Image.new("RGB", (10, 10), "white")
    draw = ImageDraw.Draw(scratch)
    label_width = max(int(content_width * 0.13), int(text_width(draw, "店員", bold) + 22))
    text_width_limit = content_width - label_width - 28
    row_gap = 8
    line_gap = 5
    padding_y = 10
    line_height = int(max(text_bbox_height(draw, "あ", font), text_bbox_height(draw, "あ", bold)) * 1.25)

    laid_out = []
    total_height = 0
    for speaker, lines in rows:
        wrapped_lines = []
        for line in lines:
            wrapped_lines.extend(wrap_text(draw, line, font, text_width_limit))
        if not wrapped_lines:
            wrapped_lines = [""]
        row_height = padding_y * 2 + len(wrapped_lines) * line_height + max(0, len(wrapped_lines) - 1) * line_gap
        laid_out.append(
            {
                "speaker": speaker,
                "lines": wrapped_lines,
                "height": row_height,
            }
        )
        total_height += row_height + row_gap

    return {
        "rows": laid_out,
        "height": max(0, total_height - row_gap),
        "label_width": label_width,
        "line_height": line_height,
        "line_gap": line_gap,
        "row_gap": row_gap,
        "padding_y": padding_y,
        "content_width": content_width,
    }


def draw_page(layout, width, height, margin, font, bold, Image, ImageDraw, truncate=False):
    image = Image.new("RGB", (width, height), "#ffffff")
    draw = ImageDraw.Draw(image)
    x = margin
    y = margin
    max_y = height - margin
    label_width = layout["label_width"]
    line_height = layout["line_height"]
    line_gap = layout["line_gap"]
    content_width = layout["content_width"]

    draw.rectangle((margin - 4, margin - 4, width - margin + 4, height - margin + 4), outline="#d1d5db", width=2)

    for row in layout["rows"]:
        row_height = row["height"]
        if y + row_height > max_y:
            if truncate:
                draw.text((x, max_y - line_height), "以下省略", fill="#6b7280", font=font)
            break

        label_fill = "#e0f2fe" if row["speaker"] == "店員" else "#fef3c7"
        draw.rectangle((x, y, x + content_width, y + row_height), fill="#ffffff", outline="#cbd5e1", width=1)
        draw.rectangle((x, y, x + label_width, y + row_height), fill=label_fill, outline="#cbd5e1", width=1)
        draw.text((x + 10, y + 10), row["speaker"], fill="#111827", font=bold)

        line_y = y + 10
        text_x = x + label_width + 14
        for line in row["lines"]:
            draw.text((text_x, line_y), line, fill="#111827", font=font)
            line_y += line_height + line_gap
        y += row_height + layout["row_gap"]

    return image


def wrap_text(draw, text, font, max_width):
    text = str(text)
    if not text:
        return [""]
    lines = []
    current = ""
    for char in text:
        candidate = current + char
        if current and text_width(draw, candidate, font) > max_width:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def text_width(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def text_bbox_height(draw, text, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[3] - bbox[1]
