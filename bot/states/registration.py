from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SelfReg(StatesGroup):
    """FSM for user self-registration."""

    language = State()
    full_name = State()
    birth_date = State()
    phone = State()
    face_condition = State()


class AdminAssistedReg(StatesGroup):
    """FSM for admin-assisted registration."""

    language = State()
    full_name = State()
    birth_date = State()
    phone = State()
    face_condition = State()


class SkinQuizState(StatesGroup):
    """
    FSM for the 10-question skin quiz.

    Reached both from registration (right after the phone number) and from the
    profile screen later on. Which one it is comes from the FSM *data*, not a
    separate state: the registration answers already sit there, so the quiz can
    hand control back to the exact step it interrupted.
    """

    intro = State()
    answering = State()


class ProgressState(StatesGroup):
    """FSM for week-2 before/after photo collection."""

    before_photo = State()
    after_photo = State()


class SupportState(StatesGroup):
    """FSM for free-form questions/messages to the shop."""

    message = State()


class FaceAnalysisState(StatesGroup):
    """FSM for the standalone «Yuz tahlili» menu button."""

    photo = State()
