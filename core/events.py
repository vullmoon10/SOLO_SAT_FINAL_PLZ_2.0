"""키 입력을 받아 퀴즈 선택, 제출, 닫기를 처리한다."""

import pygame


# 키보드와 마우스 입력을 퀴즈 선택·제출 동작으로 변환한다.
def handle_quiz_event(event, quiz, apply_result):
    choices = quiz.enemy.question["choices"]
    # 키 입력 종류에 맞춰 퀴즈를 닫거나 답을 선택·제출한다.
    if event.type == pygame.KEYDOWN:
        # ESC는 현재 퀴즈를 닫는다.
        if event.key == pygame.K_ESCAPE:
            quiz.enemy = None
        # 위쪽 키는 선택 번호를 한 칸 뒤로 옮긴다.
        elif event.key in (pygame.K_UP, pygame.K_w):
            quiz.selected = (quiz.selected - 1) % len(choices)
        # 아래쪽 키는 선택 번호를 한 칸 앞으로 옮긴다.
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            quiz.selected = (quiz.selected + 1) % len(choices)
        # Enter와 Space는 현재 선택 답을 제출한다.
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            apply_result(quiz.submit(quiz.selected))
        # 숫자 키는 해당 번호가 실제 선택지 범위 안에 있을 때 제출한다.
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
            index = event.key - pygame.K_1
            # 해당 번호에 보기가 존재할 때만 답으로 제출한다.
            if index < len(choices):
                apply_result(quiz.submit(index))
    # 마우스 왼쪽 클릭은 클릭한 선택지를 찾아 제출한다.
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        # 그림 문제는 우측 선택지 배치, 일반 문제는 전체 너비 배치를 사용한다.
        if quiz.enemy.question.get("page_image_bytes"):
            left, width, top, row_h = 600, 350, 130, 70
        # 일반 문제는 전체 폭을 선택지 영역으로 사용한다.
        else:
            left, width, top = 45, 910, 125
            row_h = min(70, 380 // max(1, len(choices)))
        # 클릭 좌표가 각 선택지 사각형 안에 들어오는지 검사한다.
        for index in range(len(choices)):
            # 선택지 영역을 누른 경우 해당 인덱스의 답을 제출한다.
            if pygame.Rect(left, top + index * row_h, width, row_h - 8).collidepoint(event.pos):
                apply_result(quiz.submit(index))
                break
