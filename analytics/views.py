from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from interviews.models import InterviewSession
from responses.models import Answer


def _clamp(val, default=0):
    try:
        v = float(val)
        return max(0, min(100, round(v)))
    except Exception:
        return default


def _performance_label(score: float) -> str:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Average"
    return "Needs Improvement"


@login_required
def overview(request):
    sessions = InterviewSession.objects.filter(user=request.user).order_by('-start_time')
    aggregates = sessions.aggregate(
        avg_tech=Avg('technical_score'),
        avg_comm=Avg('communication_score'),
        avg_conf=Avg('confidence_score'),
        total=Count('id'),
    )

    t = round(aggregates.get('avg_tech') or 0, 1)
    c = round(aggregates.get('avg_comm') or 0, 1)
    conf = round(aggregates.get('avg_conf') or 0, 1)

    avg_skills = {
        'Communication': c,
        'Technical Knowledge': t,
        'Problem Solving': _clamp(0.9 * t + 0.1 * conf, t),
        'Confidence': conf,
        'Clarity': _clamp(0.95 * c + 0.05 * conf, c),
    }

    context = {
        'sessions': sessions,
        'avg_tech': t,
        'avg_comm': c,
        'avg_conf': conf,
        'total_sessions': aggregates.get('total') or 0,
        'avg_skills': avg_skills,
    }
    return render(request, 'analytics/overview.html', context)


@login_required
def session_detail(request, session_id: int):
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    questions = session.questions.order_by('order')
    answers = Answer.objects.filter(session=session).select_related('question')
    answer_by_question = {ans.question_id: ans for ans in answers}

    qa = []
    for q in questions:
        qa.append({
            'order': q.order,
            'question': q.question_text,
            'answer': answer_by_question.get(q.id),
        })

    tech = _clamp(session.technical_score, 70)
    comm = _clamp(session.communication_score, 70)
    conf = _clamp(session.confidence_score, 70)

    skills = {
        'Communication': comm,
        'Technical Knowledge': tech,
        'Problem Solving': _clamp(0.9 * tech + 0.1 * conf, tech),
        'Confidence': conf,
        'Clarity': _clamp(0.95 * comm + 0.05 * conf, comm),
        'Response Structure': _clamp(0.9 * comm + 0.1 * tech, comm),
        'Practical Understanding': _clamp(0.95 * tech + 0.05 * comm, tech),
        'Coding/Logical Thinking': _clamp(tech, tech),
    }

    skill_rows = [{'label': k, 'value': v} for k, v in skills.items()]

    overall_score = _clamp(sum(skills.values()) / len(skills), 70)
    percentile = max(1, min(99, round(overall_score * 0.95)))
    performance_label = _performance_label(overall_score)
    ai_confidence = _clamp(conf or overall_score, overall_score)

    sorted_skills = sorted(skills.items(), key=lambda kv: kv[1])
    weak_areas = sorted_skills[:3]
    weak_suggestions = []
    for name, score in weak_areas:
        suggestion = "Focus on deepening examples and practicing aloud." if score < 70 else "Refine with targeted drills."
        weak_suggestions.append({'name': name, 'score': score, 'suggestion': suggestion})

    duration = None
    if session.start_time:
        end_time = session.end_time or timezone.now()
        duration_delta = end_time - session.start_time
        duration = str(duration_delta).split('.')[0]

    context = {
        'session': session,
        'qa': qa,
        'skills': skills,
        'overall_score': overall_score,
        'performance_label': performance_label,
        'percentile': percentile,
        'ai_confidence': ai_confidence,
        'weak_suggestions': weak_suggestions,
        'duration': duration,
        'skill_rows': skill_rows,
    }
    return render(request, 'analytics/session_detail.html', context)
