from aiogram.fsm.state import State, StatesGroup


class PaymentStates(StatesGroup):
    waiting_screenshot = State()


class SignalStates(StatesGroup):
    coin = State()
    entry = State()
    stop = State()
    tp1 = State()
    tp2 = State()
    comment = State()
    confirm = State()


class ContentStates(StatesGroup):
    choosing_type = State()
    title = State()
    file = State()
    caption = State()
    tariff = State()


class PriceEditStates(StatesGroup):
    waiting_value = State()


class BroadcastStates(StatesGroup):
    waiting_message = State()


class ViolationStates(StatesGroup):
    waiting_user_id = State()
    waiting_note = State()
