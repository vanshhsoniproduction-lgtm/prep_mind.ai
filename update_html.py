with open("templates/interviews/schedule.html", "r") as f:
    html = f.read()

new_html = html.replace(
"""<a id="meetLink" href="#" target="_blank" style="color: #1a73e8; font-size:14px; display:block; margin-bottom: 8px;">Add to Google Calendar</a>
        <a id="meetVideoLink" href="#" target="_blank" style="color: #1a73e8; font-size:14px;">Open Google Meet</a>""",
"""<a id="meetVideoLink" href="#" target="_blank" style="color: #1a73e8; font-size:14px; display:block;">Open Google Meet</a>
        <a id="meetLink" href="#" target="_blank" style="color: #1a73e8; font-size:14px; display:none;">View Event Details</a>""")

with open("templates/interviews/schedule.html", "w") as f:
    f.write(new_html)

