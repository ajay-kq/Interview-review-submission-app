from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def fit_text(c, text, x, y, max_width, font_name="Helvetica", font_size=10):
    value = text or "-"
    c.setFont(font_name, font_size)

    while c.stringWidth(value, font_name, font_size) > max_width and len(value) > 3:
        value = value[:-4] + "..."

    c.drawString(x, y, value)


def draw_wrapped_lines(c, text, x, y, max_width, line_height=11.5, font_name="Helvetica", font_size=10):
    c.setFont(font_name, font_size)
    value = (text or "-").replace("\r", " ").replace("\n", " ")
    words = value.split()

    if not words:
        c.drawString(x, y, "-")
        return y - line_height

    lines = []
    current = ""

    for word in words:
        test = word if not current else current + " " + word
        if c.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word

    if current:
        lines.append(current)

    for line in lines:
        c.drawString(x, y, line)
        y -= line_height

    return y


def draw_watermark(c, width, height):
    c.saveState()
    c.setFillColor(colors.Color(0.75, 0.75, 0.75, alpha=0.10))
    c.setFont("Helvetica-Bold", 50)
    c.translate(width / 2, height / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, "CONFIDENTIAL")
    c.restoreState()


def draw_label_value_row(c, label_x, value_x, y, label, value, value_width):
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(label_x, y, label)
    c.setFont("Helvetica", 10)
    fit_text(c, value, value_x, y, value_width, "Helvetica", 10)


def draw_candidate_name_row(c, label_x, value_x, y, value, value_width):
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(label_x, y, "Candidate Name:")

    full_value = (value or "-").strip()
    if full_value.upper().startswith("MR. "):
        full_value = "Mr. " + full_value[4:].strip()
    elif full_value.upper() == "MR.":
        full_value = "Mr."

    if full_value.startswith("Mr. "):
        prefix = "Mr."
        rest = full_value[3:].strip()

        c.setFont("Helvetica-Bold", 10)
        c.drawString(value_x, y, prefix)

        prefix_width = c.stringWidth(prefix + " ", "Helvetica-Bold", 10)
        c.setFont("Helvetica-Bold", 10)

        while c.stringWidth(" " + rest, "Helvetica-Bold", 10) > (value_width - prefix_width) and len(rest) > 3:
            rest = rest[:-4] + "..."

        c.drawString(value_x + prefix_width, y, " " + rest)
    else:
        c.setFont("Helvetica-Bold", 10)
        fit_text(c, full_value, value_x, y, value_width, "Helvetica-Bold", 10)


def build_pdf_report(review, ratings, output_path: Path):
    c = canvas.Canvas(str(output_path), pagesize=A4)
    width, height = A4

    margin = 12 * mm
    usable_width = width - (2 * margin)

    draw_watermark(c, width, height)

    header_h = 20 * mm
    c.setFillColor(colors.HexColor("#26408b"))
    c.rect(0, height - header_h, width, header_h, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(width / 2, height - 12 * mm, "IT Infrastructure Team – Interview Review Report")

    y = height - 30 * mm

    left_label_x = margin
    left_value_x = margin + 40 * mm
    right_block_x = width - 72 * mm
    right_box_w = 48 * mm
    right_box_h = 9 * mm

    draw_candidate_name_row(c, left_label_x, left_value_x, y, review["candidate_name"] or "-", 75 * mm)
    draw_label_value_row(c, left_label_x, left_value_x, y - 10 * mm, "Position:", review["position"] or "-", 75 * mm)
    draw_label_value_row(c, left_label_x, left_value_x, y - 20 * mm, "Interviewer:", review["interviewer_name"] or "-", 75 * mm)
    draw_label_value_row(c, left_label_x, left_value_x, y - 30 * mm, "Date:", review["interview_date"] or "-", 75 * mm)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(right_block_x, y, "Recommendation Status")

    c.setFillColor(colors.HexColor("#dbe4f4"))
    c.roundRect(right_block_x, y - 10 * mm, right_box_w, right_box_h, 3 * mm, fill=1, stroke=0)

    rec_raw = review["recommendation"] or "-"
    rec_value = rec_raw.strip().lower()
    rec_color = colors.HexColor("#26408b")
    if rec_value == "selected":
        rec_color = colors.HexColor("#15803d")
    elif rec_value == "hold":
        rec_color = colors.HexColor("#d97706")
    elif rec_value in ("skip", "not recommended"):
        rec_color = colors.HexColor("#dc2626")

    c.setFillColor(rec_color)
    c.setFont("Helvetica-Bold", 10.5)
    fit_text(
        c,
        rec_raw.upper(),
        right_block_x + 5 * mm,
        y - 6.7 * mm,
        right_box_w - 10 * mm,
        "Helvetica-Bold",
        10.5
    )

    y -= 40 * mm

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 12.5)
    c.drawString(margin, y, "Selected Skills & Ratings")
    y -= 8 * mm

    table_x = margin
    rating_col_x = table_x + 112 * mm

    c.setFillColor(colors.HexColor("#eef2f7"))
    c.rect(table_x, y - 3.5, usable_width, 6.5 * mm, fill=1, stroke=0)

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(table_x + 3, y - 0.1, "Skill Area")
    c.drawString(rating_col_x, y - 0.1, "Rating")

    y -= 8 * mm

    if ratings:
        for row in ratings:
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 9.8)
            fit_text(c, row["skill_label"], table_x + 3, y, 100 * mm, "Helvetica", 9.8)

            rating = int(row["rating"])
            score_text = f"({rating * 2}/10)"

            c.setFont("Helvetica-Bold", 10.5)
            c.setFillColor(colors.HexColor("#d4a017"))
            c.drawString(rating_col_x, y, "★" * rating)

            star_width = c.stringWidth("★" * rating, "Helvetica-Bold", 10.5)

            c.setFillColor(colors.HexColor("#1f2937"))
            c.setFont("Helvetica-Bold", 9.8)
            c.drawString(rating_col_x + star_width + 4, y, score_text)

            y -= 6.4 * mm
    else:
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        c.drawString(table_x + 3, y, "No skills selected")
        y -= 6.4 * mm

    y -= 5 * mm

    def draw_text_section(title, text):
        nonlocal y
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawString(margin, y, title)
        y -= 7 * mm

        c.setFillColor(colors.black)
        y = draw_wrapped_lines(
            c,
            text or "-",
            margin + 4,
            y,
            max_width=usable_width - 8,
            line_height=11.5,
            font_name="Helvetica",
            font_size=10
        )

        y -= 8 * mm

    draw_text_section("Profile Summary", review["profile_summary"])
    draw_text_section("Technical Evaluation", review["technical_evaluation"])
    draw_text_section("Observations", review["observations"])
    draw_text_section("Overall Assessment", review["overall_assessment"])

    c.setFillColor(colors.HexColor("#444444"))
    c.setFont("Helvetica-Bold", 10.5)
    c.drawCentredString(width / 2, 11 * mm, "Thankyou !")

    c.save()