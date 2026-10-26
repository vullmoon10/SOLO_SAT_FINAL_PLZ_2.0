"""정답 보상 점수를 누적하는 진행 시스템."""

def add_score(current_score, earned_score):  # 음수가 아닌 획득 점수를 현재 점수에 더
    """획득 점수를 누적한다."""
    return current_score + max(0, earned_score)
