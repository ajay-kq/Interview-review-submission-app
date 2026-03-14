import requests


def recommendation_status_text(value):
    value = (value or "").strip().lower()
    if value == "selected":
        return "🟢 SELECTED"
    if value == "hold":
        return "🟠 HOLD"
    if value == "skip":
        return "🔴 SKIP"
    if value == "not recommended":
        return "🔴 NOT RECOMMENDED"
    return f"🔵 {value.upper()}" if value else "-"


def safe_html(text):
    return (text or "-").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def shorten_skill_label(skill):
    skill = (skill or "-").strip()
    replacements = {
        "Infrastructure Management": "Infrastructure Mgmt",
        "General - IT Administration": "General - IT Admin",
        "Basic - IT Administration": "Basic - IT Admin",
    }
    return replacements.get(skill, skill)


def build_star_rating(score, total=10):
    score = max(0, min(total, score))
    return "★" * score + "☆" * (total - score)


def build_skill_widgets(selected_skills):
    """
    keyValue widget per skill:
      topLabel  = skill name (small label above)
      content   = ★★★★☆☆☆☆☆☆  4/10  (always starts at same x)

    Since 'content' is the main body of keyValue, it is always
    left-aligned at the same position regardless of topLabel length.
    Stars are guaranteed to start at the same point for every row.
    """
    if not selected_skills:
        return [{"textParagraph": {"text": "No skills selected"}}]

    widgets = []
    for item in selected_skills:
        skill = safe_html(shorten_skill_label(item.get("skill", "-")))
        try:
            score = int(item.get("score_10", 0))
        except Exception:
            score = 0
        score = max(0, min(10, score))
        stars = build_star_rating(score)

        widgets.append({
            "keyValue": {
                "topLabel": skill,
                "content": f"{stars}  {score}/10",
                "contentMultiline": "false"
            }
        })

    return widgets


def send_to_google_chat(
    webhook_url,
    candidate_name,
    position,
    interview_date,
    interviewer_name,
    selected_skills,
    recommendation,
    profile_summary,
    technical_evaluation
):
    try:
        if not webhook_url:
            return False, "Webhook URL is empty"

        skill_widgets = build_skill_widgets(selected_skills)

        title = (
            f"Interview Review for <b>{safe_html(candidate_name)}</b> | "
            f"Interview Date: {safe_html(interview_date)}"
        )

        payload = {
            "cards": [
                {
                    "sections": [
                        {
                            "widgets": [
                                {"textParagraph": {"text": title}}
                            ]
                        },
                        {
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": f"<b>Profile Summary</b><br>{safe_html(profile_summary)}"
                                    }
                                }
                            ]
                        },
                        {
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": f"<b>Technical Evaluation</b><br>{safe_html(technical_evaluation)}"
                                    }
                                }
                            ]
                        },
                        {
                            "header": "Skills &amp; Ratings",
                            "widgets": skill_widgets
                        },
                        {
                            "widgets": [
                                {
                                    "textParagraph": {
                                        "text": (
                                            f"<b>Final Recommendation</b><br>"
                                            f"<b>Status:</b> <b>{recommendation_status_text(recommendation)}</b>"
                                        )
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        response = requests.post(webhook_url, json=payload, timeout=20)

        if response.status_code in (200, 204):
            return True, "Webhook sent successfully"

        return False, f"HTTP {response.status_code} - {response.text}"

    except Exception as exc:
        return False, str(exc)