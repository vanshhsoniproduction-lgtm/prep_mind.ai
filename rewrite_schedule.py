import re

html_content = """{% extends 'base.html' %}

{% block content %}
<style>
    body {
        background-color: #f8f9fa !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
    }
    .pixel-card {
        background: #ffffff;
        border-radius: 24px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        padding: 32px;
        max-width: 500px;
        margin: 40px auto;
        color: #202124;
    }
    .pixel-input {
        width: 100%;
        padding: 12px 16px;
        border: 1px solid #dadce0;
        border-radius: 8px;
        font-size: 16px;
        margin-top: 8px;
        margin-bottom: 24px;
        outline: none;
        transition: border-color 0.2s;
    }
    .pixel-input:focus { border-color: #1a73e8; }
    .pixel-label { font-weight: 500; font-size: 14px; color: #5f6368; }
    .pixel-btn {
        background-color: #1a73e8;
        color: #ffffff;
        border: none;
        padding: 12px 24px;
        border-radius: 24px;
        font-weight: 500;
        cursor: pointer;
        width: 100%;
        font-size: 16px;
        transition: background-color 0.2s;
    }
    .pixel-btn:hover { background-color: #1557b0; }
    
    #successMessage { 
        display: none; 
        margin-top: 24px; 
        text-align: center; 
        padding-top: 20px;
        border-top: 1px solid #f1f3f4;
    }
    #successMessageText {
        color: #1e8e3e; 
        font-weight: 500; 
        margin-bottom: 16px;
    }

    .pixel-chip-btn {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 8px;
        padding: 10px 20px;
        border-radius: 100px;
        font-weight: 500;
        font-size: 14px;
        text-decoration: none;
        transition: all 0.2s;
        margin-top: 8px;
        width: 100%;
        box-sizing: border-box;
    }
    .btn-primary-tonal {
        background-color: #d3e3fd;
        color: #0b57d0;
    }
    .btn-primary-tonal:hover { background-color: #c2d7fa; }
    
    .btn-success-tonal {
        background-color: #c4eed0;
        color: #0d652d;
    }
    .btn-success-tonal:hover { background-color: #b3e7c3; }

    .btn-doc-tonal {
        background-color: #e5d5fa;
        color: #4f2398;
    }
    .btn-doc-tonal:hover { background-color: #d7bdf6; }

    #buttonContainer {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 12px;
        align-items: center;
    }
</style>

<div class="pixel-card">
    <h2 style="font-size: 24px; margin-bottom: 8px;">Schedule Next Interview</h2>
    <p style="color: #5f6368; font-size: 14px; margin-bottom: 32px;">Pick a date for your next PrepMind AI mock assessment.</p>
    
    <label class="pixel-label">Title</label>
    <input type="text" id="schedTitle" class="pixel-input" value="PrepMind AI Mock Interview" />
    
    <label class="pixel-label">Date</label>
    <input type="date" id="schedDate" class="pixel-input" />

    <label class="pixel-label">Time</label>
    <input type="time" id="schedTime" class="pixel-input" />

    <button id="schedBtn" class="pixel-btn">Schedule Interview</button>

    <div id="successMessage">
        <p id="successMessageText">Interview scheduled successfully in your Google Calendar!</p>
        <div id="buttonContainer"></div>
    </div>
</div>

<script>
    document.getElementById('schedBtn').addEventListener('click', async () => {
        const title = document.getElementById('schedTitle').value;
        const date = document.getElementById('schedDate').value;
        const time = document.getElementById('schedTime').value;

        if(!date || !time) return alert("Please select date and time.");

        const btn = document.getElementById('schedBtn');
        btn.innerText = "Scheduling...";
        btn.disabled = true;

        try {
            const res = await fetch('/interviews/api/schedule-interview/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
                body: JSON.stringify({ title, date, time })
            });
            const data = await res.json();
            
            if(data.success) {
                document.getElementById('successMessage').style.display = 'block';
                const btnContainer = document.getElementById('buttonContainer');
                btnContainer.innerHTML = '';
                
                // Add Meet button
                btnContainer.innerHTML += `
                    <a href="${data.meet_link}" target="_blank" class="pixel-chip-btn btn-success-tonal">
                        <span class="material-symbols-rounded" style="font-size:20px">videocam</span> 
                        Open Google Meet
                    </a>
                `;

                // Handle Calendar Intent based on fallback
                if(data.event_link.includes('render?action=TEMPLATE')) {
                    document.getElementById('successMessageText').innerText = "Looks like Google Calendar isn't fully integrated yet. You can add it manually:";
                    document.getElementById('successMessageText').style.color = "#ea4335";
                    btnContainer.innerHTML += `
                        <a href="${data.event_link}" target="_blank" class="pixel-chip-btn btn-primary-tonal">
                            <span class="material-symbols-rounded" style="font-size:20px">calendar_add_on</span> 
                            Add to Google Calendar
                        </a>
                    `;
                } else {
                    document.getElementById('successMessageText').innerText = "Interview automatically saved directly into your Google Calendar!";
                    document.getElementById('successMessageText').style.color = "#1e8e3e";
                    btnContainer.innerHTML += `
                        <a href="${data.event_link}" target="_blank" class="pixel-chip-btn btn-primary-tonal">
                            <span class="material-symbols-rounded" style="font-size:20px">event</span> 
                            View Event details
                        </a>
                    `;
                }
                
                btn.innerText = "Scheduled!";
                
                // Trigger Background Report generation too
                const params = new URLSearchParams(window.location.search);
                const sessionId = params.get('session_id');
                if(sessionId) {
                    fetch('/interviews/api/create-doc-report/', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': '{{ csrf_token }}' },
                        body: JSON.stringify({ session_id: sessionId })
                    }).then(r => r.json()).then(d => {
                        if(d.success && !d.doc_link.includes('mock_doc_id')) {
                            btnContainer.innerHTML += `
                                <a href="${d.doc_link}" target="_blank" class="pixel-chip-btn btn-doc-tonal">
                                    <span class="material-symbols-rounded" style="font-size:20px">description</span> 
                                    View AI Report
                                </a>
                            `;
                        }
                    });
                }
            } else {
                alert("Failed to schedule.");
                btn.innerText = "Schedule Interview";
                btn.disabled = false;
            }
        } catch(err) {
            console.error(err);
            btn.innerText = "Schedule Interview";
            btn.disabled = false;
        }
    });

    // Default dates
    document.getElementById('schedDate').valueAsDate = new Date();
</script>
{% endblock %}"""

with open("templates/interviews/schedule.html", "w") as f:
    f.write(html_content)

print("Rewrote schedule.html successfully.")
