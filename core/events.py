"""키 입력을 받아 퀴즈 선택, 제출, 닫기를 처리한다."""

import pygame


def handle_quiz_event(event, quiz, apply_result):
    choices = quiz.enemy.question["choices"]
    if event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            quiz.enemy = None
        elif event.key in (pygame.K_UP, pygame.K_w):
            quiz.selected = (quiz.selected - 1) % len(choices)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            quiz.selected = (quiz.selected + 1) % len(choices)
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            apply_result(quiz.submit(quiz.selected))
        elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
            index = event.key - pygame.K_1
            if index < len(choices):
                apply_result(quiz.submit(index))
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if quiz.enemy.question.get("page_image_bytes"):
            left, width, top, row_h = 600, 350, 130, 70
        else:
            left, width, top = 45, 910, 125
            row_h = min(70, 380 // max(1, len(choices)))
        for index in range(len(choices)):
            if pygame.Rect(left, top + index * row_h, width, row_h - 8).collidepoint(event.pos):
                apply_result(quiz.submit(index))
                break
