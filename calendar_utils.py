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

def get_event_days(reminders, year, month):
    event_days = {} # Maps day (int) to list of events {name, time, color}
    colors = ['#ff4d4d', '#4da6ff', '#bf4dff', '#4dff4d', '#ffa64d', '#ff66b3', '#33cccc']
    
    first_day = datetime.datetime(year, month, 1, tzinfo=datetime.timezone.utc)
    next_month_day = 28
    temp_next = first_day.replace(day=next_month_day) + datetime.timedelta(days=4)
    last_day = temp_next - datetime.timedelta(days=temp_next.day)

    def _parse_date(date_str):
        if not date_str:
            return datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=datetime.timezone.utc)

    for i, reminder in enumerate(reminders):
        # Depending on if it's get_all_reminders_full or get_reminders, it usually has 7 fields.
        # We only really need name, time, recurrence, target_date.
        # For safety we use negative indexing for known fields or unpack properly if size is known
        # In bot.py it's: rid, event_name, target_time, channel_id, gif_url, recurrence, target_date
        event_name = reminder[1]
        target_time = reminder[2]
        recurrence = reminder[-2]
        target_date = reminder[-1]
        
        color = colors[i % len(colors)]
        days_for_this_event = []
        
        if recurrence == 'daily':
            days_for_this_event = list(range(1, last_day.day + 1))
        elif recurrence == 'once' and target_date:
            try:
                dt = _parse_date(target_date)
                if dt.year == year and dt.month == month:
                    days_for_this_event.append(dt.day)
            except Exception: pass
        elif recurrence == 'weekly' and target_date:
            try:
                dt = _parse_date(target_date)
                target_weekday = dt.weekday()
                for d in range(1, last_day.day + 1):
                    current_dt = datetime.datetime(year, month, d, tzinfo=datetime.timezone.utc)
                    if current_dt.weekday() == target_weekday:
                        days_for_this_event.append(d)
            except Exception: pass
        elif recurrence == 'monthly' and target_date:
            try:
                dt = _parse_date(target_date)
                if dt.day <= last_day.day:
                    days_for_this_event.append(dt.day)
            except Exception: pass
        elif recurrence == 'every_other_day' and target_date:
            try:
                dt = _parse_date(target_date)
                curr = dt
                while curr < first_day:
                    curr += datetime.timedelta(days=2)
                while curr <= last_day:
                    if curr.month == month and curr.year == year:
                        days_for_this_event.append(curr.day)
                    curr += datetime.timedelta(days=2)
            except Exception: pass
        elif recurrence == 'every_other_week' and target_date:
            try:
                dt = _parse_date(target_date)
                curr = dt
                while curr < first_day:
                    curr += datetime.timedelta(days=14)
                while curr <= last_day:
                    if curr.month == month and curr.year == year:
                        days_for_this_event.append(curr.day)
                    curr += datetime.timedelta(days=14)
            except Exception: pass

        for day in days_for_this_event:
            if day not in event_days:
                event_days[day] = []
            event_days[day].append({
                'title': event_name,
                'time': target_time + " UTC",
                'color': color
            })
            
    return event_days

def generate_calendar_image(year, month, reminders):
    width, height = 900, 600
    img = Image.new('RGB', (width, height), color='#2b2d31') # Discord dark theme bg
    draw = ImageDraw.Draw(img)

    try:
        font_large = ImageFont.truetype("Roboto-Regular.ttf", 36)
        font_med = ImageFont.truetype("Roboto-Regular.ttf", 20)
        font_small = ImageFont.truetype("Roboto-Regular.ttf", 14)
        font_bold = font_med # Fallback if we don't have Roboto-Bold
    except:
        font_large = ImageFont.load_default()
        font_med = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_bold = font_med

    # Split: Left 60% Calendar, Right 40% Events List
    margin = 30
    cal_width = int((width - 2*margin) * 0.6)
    
    month_name = calendar.month_name[month]
    title = f"{month_name} {year}"
    
    draw.text((margin, margin), title, fill='#ffffff', font=font_large)

    # Days of week
    days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    col_w = cal_width / 7
    start_y = margin + 60
    
    for i, d in enumerate(days):
        bbox = draw.textbbox((0, 0), d, font=font_med)
        tw = bbox[2] - bbox[0]
        draw.text((margin + i*col_w + col_w/2 - tw/2, start_y), d, fill='#b5bac1', font=font_med)

    event_data = get_event_days(reminders, year, month)
    cal = calendar.monthcalendar(year, month)
    
    # Adjust calendar to start on Sunday
    # monthcalendar has Monday=0, so Sunday=6
    for i in range(len(cal)):
        # week is [Mon, Tue, Wed, Thu, Fri, Sat, Sun]
        week = cal[i]
        cal[i] = [week[-1]] + week[:-1]
    
    # if the first day was Sunday, it wrapped to the first position perfectly,
    # but if the first week was [0,0...,1] (meaning Sunday was 1) monthcalendar puts 1 at the end of week 0.
    # Let's cleanly recreate the grid starting on Sunday.
    
    first_weekday = datetime.date(year, month, 1).weekday() # Mon=0, Sun=6
    first_weekday_sun_start = (first_weekday + 1) % 7 # Sun=0, Mon=1
    
    _, days_in_month = calendar.monthrange(year, month)
    
    grid = []
    current_week = [0]*7
    current_day_idx = first_weekday_sun_start
    day = 1
    
    while day <= days_in_month:
        current_week[current_day_idx] = day
        day += 1
        current_day_idx += 1
        if current_day_idx > 6:
            grid.append(current_week)
            current_week = [0]*7
            current_day_idx = 0
            
    if current_day_idx > 0:
        grid.append(current_week)

    row_h = (height - start_y - 40) / max(len(grid), 5)
    grid_y = start_y + 30

    today = datetime.datetime.now(datetime.timezone.utc)

    # Draw Calendar Grid
    for r, week in enumerate(grid):
        for c, day in enumerate(week):
            if day == 0:
                continue
                
            x = margin + c * col_w
            y = grid_y + r * row_h
            
            # Cell bg
            cell_rect = [x+2, y+2, x+col_w-4, y+row_h-4]
            is_today = (today.year == year and today.month == month and today.day == day)
            
            if is_today:
                draw_rounded_rect(draw, cell_rect, 8, fill='#313338')
                draw.rounded_rectangle(cell_rect, radius=8, outline='#5865F2', width=2)
            else:
                draw_rounded_rect(draw, cell_rect, 8, fill='#313338')
                
            # Day number
            draw.text((x + 8, y + 4), str(day), fill=('#ffffff' if is_today else '#dbdee1'), font=font_med)
            
            # Draw event dots
            if day in event_data:
                day_events = event_data[day]
                dot_radius = 4
                dot_y = y + row_h - 15
                total_w = (len(day_events) * (dot_radius*2 + 4)) - 4
                dot_x = x + (col_w / 2) - (total_w / 2)
                
                for ev in day_events[:5]: # Max 5 dots visually
                    c_color = ev['color']
                    draw.ellipse([dot_x, dot_y, dot_x+dot_radius*2, dot_y+dot_radius*2], fill=c_color)
                    dot_x += dot_radius*2 + 4

    # Draw Side Panel (Events List)
    list_x = margin + cal_width + 30
    list_y = margin
    right_margin = width - margin
    
    draw_rounded_rect(draw, [list_x, list_y, right_margin, height-margin], 12, fill='#232428')
    draw.text((list_x + 20, list_y + 20), "Upcoming Events", fill='#ffffff', font=font_med)
    
    y_offset = list_y + 60
    
    # Flatten and sort events uniquely
    unique_events = {}
    
    for day, evs in event_data.items():
        if day < today.day and today.year == year and today.month == month:
            continue # skip passed events for list, unless not current month
            
        for ev in evs:
            key = f"{ev['title']}_{ev['time']}"
            if key not in unique_events:
                # Store one representation per event (we don't list an event 30 times if it's daily)
                unique_events[key] = {
                    'title': ev['title'],
                    'time': ev['time'],
                    'color': ev['color'],
                    'next_day': day
                }
    
    sorted_events = sorted(list(unique_events.values()), key=lambda x: x['next_day'])
    
    if not sorted_events:
        draw.text((list_x + 20, y_offset), "No upcoming events.", fill='#b5bac1', font=font_small)
    else:
        for ev in sorted_events[:10]: # show up to 10 events
            # Event Color dot
            draw.ellipse([list_x + 20, y_offset + 5, list_x + 30, y_offset + 15], fill=ev['color'])
            
            # Title
            draw.text((list_x + 40, y_offset), ev['title'], fill='#ffffff', font=font_med)
            
            # Time & Date info
            info_str = f"Time: {ev['time']}"
            draw.text((list_x + 40, y_offset + 25), info_str, fill='#b5bac1', font=font_small)
            
            y_offset += 60

    # Save to BytesIO
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf
