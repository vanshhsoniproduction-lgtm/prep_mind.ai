import re

html_to_add = """
<!-- PIXEL CALENDAR CARD -->
<style>
.g-cal-card {
    background: #ffffff;
    border-radius: 20px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    padding: 24px;
    margin-top: 24px;
    color: #202124;
}
.g-cal-title { font-size: 18px; font-weight: 500; margin-bottom: 20px; color: #202124; }
.g-cal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 8px; }
.g-cal-day {
    aspect-ratio: 1;
    border-radius: 8px;
    background: #f1f3f4;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    color: #5f6368;
    position: relative;
    cursor: default;
    transition: transform 0.2s;
}
.g-cal-day.active { background: #34a853; color: white; cursor: pointer; }
.g-cal-day.active:hover { transform: scale(1.05); }
.g-cal-tooltip {
    display: none;
    position: absolute;
    bottom: 110%;
    left: 50%;
    transform: translateX(-50%);
    background: #202124;
    color: white;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 12px;
    width: max-content;
    z-index: 10;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
}
.g-cal-day.active:hover .g-cal-tooltip { display: block; }
</style>

<div class="max-w-7xl mx-auto mt-6" style="margin-bottom: 40px;">
    <div class="g-cal-card">
        <div class="g-cal-title">Interview Activity</div>
        <div class="g-cal-grid" id="calendarGrid"></div>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', () => {
    const grid = document.getElementById('calendarGrid');
    if(!grid) return;
    const daysInMonth = 31;
    
    // Using purely UI mockup as requested
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
<!-- /PIXEL CALENDAR CARD -->
"""

with open('templates/core/dashboard.html', 'r+', encoding='utf-8') as f:
    text = f.read()
    if 'PIXEL CALENDAR CARD' not in text:
        # Replace immediately before </main>
        text = text.replace('</main>', html_to_add + '\n</main>')
        f.seek(0)
        f.write(text)
        f.truncate()
        print("Success")
    else:
        print("Already injected")
