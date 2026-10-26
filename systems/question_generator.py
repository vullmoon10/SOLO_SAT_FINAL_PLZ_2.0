"""Generate original math questions for grades 3 through middle school 1st semester."""

import random
from fractions import Fraction

QUESTION_KINDS = {
    "easy": {
        "산술": ("multiply", "divide", "add_subtract"),
        "분수": ("fraction",),
        "측정·도형": ("perimeter", "area", "time"),
    },
    "medium": {
        "수와 연산": ("integers", "rational"),
        "문자와 식": ("expression", "equation"),
        "좌표": ("coordinate",),
    },
    "hard": {
        "수와 연산": ("integers", "rational"),
        "문자와 식": ("expression", "equation"),
        "좌표": ("coordinate",),
    },
    "expert": {
        "수와 연산": ("integers", "rational"),
        "문자와 식": ("expression", "equation"),
        "좌표": ("coordinate",),
    },
}


def _format(value):
    if isinstance(value, Fraction):
        return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
    return str(value)


def _multiple_choice(prompt, answer, distractors, difficulty, domain):
    values = list(dict.fromkeys([answer, *distractors]))
    candidate = 1
    while len(values) < 4:
        value = f"{answer} (보기 {candidate})" if isinstance(answer, str) else answer + candidate
        if value not in values:
            values.append(value)
        candidate += 1
    random.shuffle(values)
    return {
        "id": f"generated-{random.getrandbits(64):016x}",
        "subject": "수학",
        "difficulty": difficulty,
        "domain": domain,
        "q": prompt,
        "choices": [_format(value) for value in values],
        "answer": values.index(answer),
        "time": {"easy": 30, "medium": 45, "hard": 60, "expert": 75}[difficulty],
        "generated": True,
    }


def _easy_question(kind, domain):
    if kind == "multiply":
        a, b = random.randint(3, 30), random.randint(2, 9)
        answer = a * b
        return _multiple_choice(f"{a} × {b}는 얼마인가요?", answer,
                                [answer + a, answer - a, a + b], "easy", domain)
    if kind == "divide":
        divisor, quotient = random.randint(2, 9), random.randint(3, 30)
        dividend = divisor * quotient
        return _multiple_choice(f"{dividend} ÷ {divisor}는 얼마인가요?", quotient,
                                [quotient + 1, quotient - 1, divisor], "easy", domain)
    if kind == "add_subtract":
        a, b = random.randint(100, 999), random.randint(100, 999)
        if random.choice((True, False)):
            answer = a + b
            prompt = f"{a} + {b}는 얼마인가요?"
        else:
            a, b = max(a, b), min(a, b)
            answer = a - b
            prompt = f"{a} − {b}는 얼마인가요?"
        return _multiple_choice(prompt, answer, [answer + 10, answer - 10, answer + 100], "easy", domain)
    if kind == "fraction":
        denominator = random.choice((2, 3, 4, 5, 6, 8, 10))
        a, b = random.randint(1, denominator - 1), random.randint(1, denominator - 1)
        op = random.choice(("+", "−"))
        if op == "−" and b > a:
            a, b = b, a
        answer = Fraction(a + b if op == "+" else a - b, denominator)
        distractors = [Fraction(a, denominator), Fraction(b, denominator), answer + Fraction(1, denominator)]
        return _multiple_choice(f"{a}/{denominator} {op} {b}/{denominator}는 얼마인가요?",
                                answer, distractors, "easy", domain)
    if kind in ("perimeter", "area"):
        width, height = random.randint(2, 15), random.randint(2, 15)
        if kind == "perimeter":
            answer = 2 * (width + height)
            prompt = f"가로가 {width} cm, 세로가 {height} cm인 직사각형의 둘레는 몇 cm인가요?"
            distractors = [width * height, width + height, answer + 2]
        else:
            answer = width * height
            prompt = f"가로가 {width} cm, 세로가 {height} cm인 직사각형의 넓이는 몇 cm²인가요?"
            distractors = [2 * (width + height), answer + width, answer - height]
        return _multiple_choice(prompt, answer, distractors, "easy", domain)

    start = random.randint(60, 180)
    elapsed = random.randint(5, 120)
    end = start + elapsed
    prompt = f"오후 {start // 60}시 {start % 60:02d}분부터 {elapsed}분이 지나면 몇 시 몇 분인가요?"
    answer = f"{(end // 60) % 12 or 12}시 {end % 60:02d}분"
    distractors = [f"{(end // 60) % 12 or 12}시 {(end + 1) % 60:02d}분",
                   f"{(end // 60) % 12 or 12}시 {(end - 1) % 60:02d}분",
                   f"{(end // 60 + 1) % 12 or 12}시 {end % 60:02d}분"]
    return _multiple_choice(prompt, answer, distractors, "easy", domain)


def _medium_question(kind, domain):
    if kind == "integers":
        a, b = random.randint(-20, 20), random.randint(-20, 20)
        op = random.choice(("+", "−", "×"))
        answer = a + b if op == "+" else a - b if op == "−" else a * b
        return _multiple_choice(f"정수 {a} {op} ({b})의 값은?", answer,
                                [-(answer), answer + 1, answer - 1], "medium", domain)
    if kind == "rational":
        d1, d2 = random.choice(((2, 3), (2, 5), (3, 4), (3, 5), (4, 5)))
        a, b = random.randint(1, d1 - 1), random.randint(1, d2 - 1)
        op = random.choice(("+", "−"))
        answer = Fraction(a, d1) + Fraction(b, d2) if op == "+" else Fraction(a, d1) - Fraction(b, d2)
        distractors = [Fraction(a, d1) + Fraction(b, d1), Fraction(a + b, d1 + d2), -answer]
        return _multiple_choice(f"{a}/{d1} {op} {b}/{d2}를 계산하면?", answer, distractors, "medium", domain)
    if kind == "expression":
        a, b, x = random.randint(2, 8), random.randint(1, 12), random.randint(-5, 8)
        answer = a * x + b
        return _multiple_choice(f"x = {x}일 때, {a}x + {b}의 값은?", answer,
                                [a * (x + b), a * x - b, answer + a], "medium", domain)
    if kind == "equation":
        a, x, b = random.randint(2, 7), random.randint(-8, 12), random.randint(-12, 15)
        c = a * x + b
        return _multiple_choice(f"{a}x + ({b}) = {c}일 때, x의 값은?", x,
                                [x + 1, x - 1, -x], "medium", domain)

    x, y = random.randint(-8, 8), random.randint(-8, 8)
    return _multiple_choice(f"좌표평면 위의 점 A({x}, {y})에서 y좌표는?", y,
                            [x, -y, y + 1], "medium", domain)


def _challenge_question(kind, domain):
    if kind == "integers":
        a, b, c = random.randint(-15, 15), random.randint(-12, 12), random.randint(2, 8)
        answer = a - b * c
        return _multiple_choice(f"정수 {a} − ({b}) × {c}의 값은?", answer,
                                [(a - b) * c, a + b * c, answer + c], "hard", domain)
    if kind == "rational":
        d1, d2 = random.choice(((4, 5), (5, 6), (6, 7), (8, 9), (10, 12)))
        a, b = random.randint(1, d1 - 1), random.randint(1, d2 - 1)
        op = random.choice(("+", "−"))
        left, right = Fraction(a, d1), Fraction(b, d2)
        answer = left + right if op == "+" else left - right
        distractors = [Fraction(a + b, d1 + d2), left - right if op == "+" else left + right,
                       answer + Fraction(1, d1 * d2)]
        return _multiple_choice(f"{a}/{d1} {op} {b}/{d2}를 계산하면?", answer, distractors, "hard", domain)
    if kind == "expression":
        a, b, c, x = random.randint(2, 7), random.randint(-9, 9), random.randint(-9, 9), random.randint(-6, 8)
        answer = a * x + b - c
        return _multiple_choice(f"x = {x}일 때, {a}x + ({b}) − ({c})의 값은?", answer,
                                [a * (x + b) - c, a * x - b - c, answer + a], "hard", domain)
    if kind == "equation":
        a, x, b = random.randint(3, 9), random.randint(-10, 10), random.randint(-15, 15)
        c = a * x + b
        return _multiple_choice(f"{a}x + ({b}) = {c}일 때, x의 값은?", x,
                                [x + 2, x - 2, -x], "hard", domain)

    x, y = random.randint(-9, 9), random.randint(-9, 9)
    while x == 0 or y == 0:
        x, y = random.randint(-9, 9), random.randint(-9, 9)
    quadrant = "제1사분면" if x > 0 and y > 0 else "제2사분면" if x < 0 < y else "제3사분면" if x < 0 and y < 0 else "제4사분면"
    distractors = ["제1사분면", "제2사분면", "제3사분면", "제4사분면"]
    distractors.remove(quadrant)
    return _multiple_choice(f"점 A({x}, {y})가 속하는 사분면은?", quadrant, distractors, "hard", domain)


def _expert_question(kind, domain):
    if kind == "integers":
        a, b, c, d = random.randint(-12, 12), random.randint(-9, 9), random.randint(2, 7), random.randint(2, 5)
        answer = a - (b + c) * d
        return _multiple_choice(f"정수 {a} − ({b} + {c}) × {d}의 값은?", answer,
                                [a - b + c * d, (a - b + c) * d, answer + d], "expert", domain)
    if kind == "rational":
        denominator = random.choice((6, 8, 10, 12))
        numerators = [random.randint(-denominator + 1, denominator - 1) for _ in range(3)]
        a, b, c = numerators
        answer = Fraction(a + b - c, denominator)
        distractors = [Fraction(a + b + c, denominator), Fraction(a - b - c, denominator),
                       Fraction(a + b - c + 1, denominator)]
        return _multiple_choice(
            f"{a}/{denominator} + ({b}/{denominator}) − ({c}/{denominator})의 값은?",
            answer, distractors, "expert", domain)
    if kind == "expression":
        a, b, c, d, x = (random.randint(2, 6), random.randint(-8, 8),
                         random.randint(2, 5), random.randint(-7, 7), random.randint(-5, 7))
        answer = a * (x + b) - c * (x + d)
        return _multiple_choice(f"x = {x}일 때, {a}(x + ({b})) − {c}(x + ({d}))의 값은?",
                                answer,
                                [a * x + b - c * x + d, (a - c) * (x + b + d), answer + a],
                                "expert", domain)
    if kind == "equation":
        a, b, x = random.randint(2, 6), random.randint(-8, 8), random.randint(-7, 9)
        c = a * (x + b)
        return _multiple_choice(f"{a}(x + ({b})) = {c}일 때, x의 값은?", x,
                                [c - b, x + b, -x], "expert", domain)

    x, y = random.randint(-8, 8), random.randint(-8, 8)
    dx, dy = random.randint(2, 6), random.randint(2, 6)
    final_x, final_y = x + dx, y - dy
    quadrant = ("제1사분면" if final_x > 0 and final_y > 0 else
                "제2사분면" if final_x < 0 < final_y else
                "제3사분면" if final_x < 0 and final_y < 0 else
                "제4사분면" if final_x > 0 > final_y else "좌표축 위")
    distractors = ["제1사분면", "제2사분면", "제3사분면", "제4사분면"]
    if quadrant == "좌표축 위":
        distractors[0] = "좌표축 위"
    else:
        distractors.remove(quadrant)
        distractors.append("좌표축 위")
    return _multiple_choice(
        f"점 A({x}, {y})를 x축 방향으로 {dx}, y축 방향으로 −{dy}만큼 옮겼다. 옮긴 점은 어느 사분면에 있나요?",
        quadrant, distractors, "expert", domain)


def generate_math_question(difficulty=None, domain=None):
    """Generate a fresh question for one of four elementary-to-middle-school tiers."""
    level = difficulty if difficulty in QUESTION_KINDS else random.choice(tuple(QUESTION_KINDS))
    if domain not in QUESTION_KINDS[level]:
        domain = random.choice(tuple(QUESTION_KINDS[level]))
    kind = random.choice(QUESTION_KINDS[level][domain])
    if level == "easy":
        return _easy_question(kind, domain)
    if level == "medium":
        return _medium_question(kind, domain)
    if level == "hard":
        return _challenge_question(kind, domain)
    return _expert_question(kind, domain)
