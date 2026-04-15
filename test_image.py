import datetime
import calendar
from PIL import Image, ImageDraw, ImageFont
import io

def draw_rounded_rect(draw, xy, radius, fill):
    x1, y1, x2, y2 = xy
    draw.rectangle([x1+radius, y1, x2-radius, y2], fill=fill)
    draw.rectangle([x1, y1+radius, x2, y2-radius], fill=fill)
    draw.pieslice([x1, y1, x1+radius*2, y1+radius*2], 180, 270, fill=fill)
    draw.pieslice([x2-radius*2, y1, x2, y1+radius*2], 270, 360, fill=fill)
    draw.pieslice([x1, y2-radius*2, x1+radius*2, y2], 90, 180, fill=fill)
    draw.pieslice([x2-radius*2, y2-radius*2, x2, y2], 0, 90, fill=fill)

def generate_calendar_image(year, month, event_days):
    width, height = 800, 500
    img = Image.new('RGB', (width, height), color='#f0f0f0') # Background
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("Roboto-Regular.ttf", 24)
        font_med = ImageFont.truetype("Roboto-Regular.ttf", 18)
        font_small = ImageFont.truetype("Roboto-Regular.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # Draw card
    card_margin = 40
    card_rect = (card_margin, card_margin, width-card_margin, height-card_margin)
    draw_rounded_rect(draw, card_rect, 20, fill='#ffffff')

    # Split card left/right
    left_width = (width - 2*card_margin) * 0.55
    right_x = card_margin + left_width
    draw.line([(right_x, card_margin), (right_x, height-card_margin)], fill='#e0e0e0', width=1)

    # Title
    month_name = calendar.month_name[month]
    title = f"{month_name} {year}"

    # Left Header bg
    header_rect = (card_margin+20, card_margin+20, right_x-20, card_margin+60)
    draw_rounded_rect(draw, header_rect, 10, fill='#f5f5f5')

    # Text
    bbox = draw.textbbox((0, 0), title, font=font_med)
    tw = bbox[2] - bbox[0]
    draw.text((card_margin+20 + (header_rect[2]-header_rect[0])/2 - tw/2, card_margin+30), title, fill='#000000', font=font_med)

    # Days of week
    days = ["S", "M", "T", "W", "T", "F", "S"]
    col_w = (right_x - card_margin - 40) / 7
    start_x = card_margin + 20
    start_y = card_margin + 80

    for i, d in enumerate(days):
        bbox = draw.textbbox((0, 0), d, font=font_med)
        tw = bbox[2] - bbox[0]
        draw.text((start_x + i*col_w + col_w/2 - tw/2, start_y), d, fill='#888888', font=font_med)

    # Grid
    cal = calendar.monthcalendar(year, month)
    row_h = 40
    grid_y = start_y + 40

    # colors
    colors = ['#ff4d4d', '#4da6ff', '#bf4dff', '#4dff4d', '#ffa64d']

    now = datetime.datetime.now()

    for r, week in enumerate(cal):
        for c, day in enumerate(week):
            # Calendar module puts Monday=0. The UI has Sunday=0.
            # We need to shift it. Let's rebuild the cal grid to start on Sunday.
            pass

    img.save("test_out.png")

generate_calendar_image(2024, 5, {24, 27, 31})
