import re

with open("templates/interviews/schedule.html", "r") as f:
    html = f.read()

# I will update the "Join Google Meet Link" to simply handle the event URL too.
new_html = html.replace(
"""<a id="meetLink" href="#" target="_blank" style="color: #1a73e8; font-size:14px;">Join Google Meet Link</a>""",
"""<a id="meetLink" href="#" target="_blank" style="color: #1a73e8; font-size:14px; display:block; margin-bottom: 8px;">Add to Google Calendar</a>
        <a id="meetVideoLink" href="#" target="_blank" style="color: #1a73e8; font-size:14px;">Open Google Meet</a>"""
)

new_html = new_html.replace(
"""document.getElementById('meetLink').href = data.meet_link;""",
"""document.getElementById('meetLink').href = data.event_link;
                document.getElementById('meetVideoLink').href = data.meet_link;"""
)

with open("templates/interviews/schedule.html", "w") as f:
    f.write(new_html)

print("Done fixing schedule html output.")
