import re

with open("templates/interviews/schedule.html", "r") as f:
    html = f.read()

# I will replace `headers: { 'Content-Type': 'application/json' },` 
# with `headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },`

new_html = html.replace(
    "headers: { 'Content-Type': 'application/json' },",
    "headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },"
)

with open("templates/interviews/schedule.html", "w") as f:
    f.write(new_html)

print("Done fixing CSRF token.")
