def ai_recommendation(scores):

    if not scores:
        return "Not Recommended"

    avg = sum(scores)/len(scores)

    if avg >= 4:
        return "Strongly Recommended"

    elif avg >= 3:
        return "Recommended"

    elif avg >= 2:
        return "Borderline"

    else:
        return "Not Recommended"