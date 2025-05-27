from aiogram.dispatcher.filters.state import State, StatesGroup

class BookingStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_date = State()
    waiting_for_phone = State()
