import re

with open("templates/core/dashboard.html", "r") as f:
    html = f.read()

# Replace everything from "<!-- PIXEL CALENDAR CARD -->" to "<!-- /PIXEL CALENDAR CARD -->"
pattern = r"<!-- PIXEL CALENDAR CARD -->.*?<!-- /PIXEL CALENDAR CARD -->"
html = re.sub(pattern, "", html, flags=re.DOTALL)

# Insert the new calendar card right after the Weekly Progress card.

split_str = """                    <div class="progress-bar-bg">
                        <div class="progress-bar-fill" style="width: {% if recent_interviews %}{% widthratio recent_interviews|length 3 100 %}%{% else %}0%{% endif %};"></div>
                    </div>
                </div>
            </div>"""

parts = html.split(split_str)

new_card = """

            <!-- PIXEL CALENDAR CARD (Sidebar style) -->
            <style>
            .g-cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px; margin-top: 12px; }
            .g-cal-day {
                aspect-ratio: 1;
                border-radius: 6px;
                background: var(--pm-bg);
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 12px;
                color: var(--pm-text-secondary);
                position: relative;
                cursor: default;
                transition: transform 0.2s;
            }
            .g-cal-day.active { background: var(--pm-green); color: white; cursor: pointer; }
            .g-cal-day.active:hover { transform: scale(1.1); }
            .g-cal-tooltip {
                display: none;
                position: absolute;
                bottom: 110%;
                left: 50%;
                transform: translateX(-50%);
                background: var(--pm-surface);
                color: var(--pm-text);
                padding: 8px 12px;
                border-radius: var(--pm-radius-sm);
                border: 1px solid var(--pm-border-light);
                font-size: 11px;
                width: max-content;
                z-index: 10;
                box-shadow: var(--pm-shadow-md);
            }
            .g-cal-day.active:hover .g-cal-tooltip { display: block; }
            </style>

            <div class="pm-card sidebar-card" style="margin-top: 0;">
                <div style="display:flex;align-items:center;gap:10px;margin-bottom:2px;">
                    <span class="material-symbols-rounded" style="color:var(--pm-primary);font-size:20px">calendar_month</span>
                    <h3 style="font-size:16px;font-weight:500;">Interview Activity</h3>
                </div>
                <div class="g-cal-grid" id="calendarGrid"></div>
            </div>

            <script>
            document.addEventListener('DOMContentLoaded', () => {
                const grid = document.getElementById('calendarGrid');
                if(!grid) return;
                const daysInMonth = 31;
                
                const mockActiveDays = {
                    12: { role: 'Software Engineer', score: '85/100', date: 'March 12, 2026' },
                    14: { role: 'Frontend Developer', score: '92/100', date: 'March 14, 2026' },
                    28: { role: 'Data Scientist', score: 'Pending', date: 'March 28, 2026' }
                };

                for(let i=1; i<=daysInMonth; i++) {
                    const dayDiv = document.createElement('div');
                    dayDiv.className = 'g-cal-day';
                    dayDiv.innerText = i;
                    
                    if(mockActiveDays[i]) {
                        dayDiv.classList.add('active');
                        const tooltip = document.createElement('div');
                        tooltip.className = 'g-cal-tooltip';
                        tooltip.innerHTML = `<strong>${mockActiveDays[i].role}</strong><br/>Score: ${mockActiveDays[i].score}<br/>${mockActiveDays[i].date}`;
                        dayDiv.appendChild(tooltip);
                    }
                    grid.appendChild(dayDiv);
                }
            });
            </script>
            <!-- /PIXEL CALENDAR CARD -->"""


if len(parts) == 2:
    new_html = parts[0] + split_str + new_card + parts[1]
    with open("templates/core/dashboard.html", "w") as f:
        f.write(new_html)
    print("Done writing.")
else:
    print("Split string not found or found multiple times.")
