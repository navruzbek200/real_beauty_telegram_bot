"""
The skin-type quiz: questions, scoring and recommendation selection.

Deliberately free of Django and of aiogram so the same rules can be reused by
the mobile app and checked by tests without a database. Everything here is
*keys* — the actual wording lives in `bot.i18n` so one rule set serves all
three languages.

Scoring follows the shop's own model, not an average of the answers:

* the skin type comes from question 1 alone — the rest of the questions are
  about separate problems (pores, pigmentation, sagging) and averaging them
  together produces a number that means nothing;
* every other question adds its own recommendation block once the answer
  reaches `THRESHOLD`, so two people with the same skin type still get
  different advice.
"""

from __future__ import annotations

from dataclasses import dataclass

# An answer this high or higher means "this is a problem for me".
THRESHOLD = 3

# The 0–5 scale every question is answered on.
MIN_ANSWER = 0
MAX_ANSWER = 5

# Question 1 decides the skin type on its own. Values match
# `TelegramUser.FaceCondition` — "sensitive" is intentionally not reachable
# here: sensitivity is a property the quiz reports separately (rec.S), not a
# type that competes with dry/oily/combination.
SKIN_TYPE_BY_Q1: dict[int, str] = {
    0: "dry",
    1: "dry",
    2: "combined",
    3: "normal",
    4: "oily",
    5: "oily",
}

# Breakouts need opposite advice depending on how oily the skin is, so this one
# question maps to two different blocks.
ACNE_RECOMMENDATION = {"oily": "rec.Ao", "other": "rec.Ad"}


@dataclass(frozen=True)
class Question:
    """One quiz question and what a high answer to it means."""

    id: str
    # i18n key of the question text.
    text_key: str
    # i18n key of the recommendation block a high answer unlocks. Empty for
    # q1 (which picks the skin type) and q4 (handled by ACNE_RECOMMENDATION).
    recommendation_key: str = ""
    # True when each option carries its own label instead of a bare digit.
    labelled_options: bool = False


QUESTIONS: tuple[Question, ...] = (
    Question("q1", "quiz.q1", labelled_options=True),
    Question("q2", "quiz.q2", "rec.P0"),
    Question("q3", "quiz.q3", "rec.S"),
    Question("q4", "quiz.q4"),  # acne — resolved against the skin type
    Question("q5", "quiz.q5", "rec.Bh"),
    Question("q6", "quiz.q6", "rec.Wh"),
    Question("q7", "quiz.q7", "rec.P"),
    Question("q8", "quiz.q8", "rec.Ew"),
    Question("q9", "quiz.q9", "rec.Ed"),
    Question("q10", "quiz.q10", "rec.W"),
)

QUESTION_COUNT = len(QUESTIONS)
QUESTION_IDS: tuple[str, ...] = tuple(q.id for q in QUESTIONS)
BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}


@dataclass(frozen=True)
class QuizResult:
    """What the quiz concluded, as keys the caller renders in any language."""

    skin_type: str
    # i18n keys, base skin-type block first, problem blocks after.
    recommendation_keys: tuple[str, ...]
    answers: dict[str, int]


def clamp(value: int) -> int:
    return max(MIN_ANSWER, min(MAX_ANSWER, value))


def analyze(answers: dict[str, int]) -> QuizResult:
    """
    Turn a full set of answers into a skin type plus its recommendation blocks.

    Missing answers count as 0 rather than raising: a half-finished quiz still
    has to produce something showable, and 0 means "not a problem", which is
    the safe reading of an unanswered question.
    """
    clean = {qid: clamp(int(answers.get(qid, 0) or 0)) for qid in QUESTION_IDS}

    skin_type = SKIN_TYPE_BY_Q1[clean["q1"]]
    keys: list[str] = [f"rec.base.{skin_type}"]

    for question in QUESTIONS:
        if clean[question.id] < THRESHOLD:
            continue
        if question.id == "q4":
            keys.append(
                ACNE_RECOMMENDATION["oily" if skin_type == "oily" else "other"]
            )
        elif question.recommendation_key:
            keys.append(question.recommendation_key)

    return QuizResult(
        skin_type=skin_type, recommendation_keys=tuple(keys), answers=clean
    )
