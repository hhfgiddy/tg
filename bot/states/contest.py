from aiogram.fsm.state import State, StatesGroup


class ContestCreateStates(StatesGroup):
    waiting_for_channel = State()
    waiting_for_post = State()
    waiting_for_required_channel = State()
    waiting_for_end_type = State()
    waiting_for_end_value = State()
    waiting_for_winners_count = State()
    waiting_for_button_text = State()
    waiting_for_start_time = State()
    waiting_for_confirmation = State()

    # Tahrirlash
    editing_menu = State()
    editing_channel = State()
    editing_post = State()
    editing_required_channel = State()
    editing_end_type = State()
    editing_end_value = State()
    editing_winners_count = State()
    editing_button_text = State()
    editing_start_time = State()