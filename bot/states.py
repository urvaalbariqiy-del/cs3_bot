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
    photo = State()
    confirm = State()


class ContentStates(StatesGroup):
    title = State()
    file = State()
    caption = State()


class PriceEditStates(StatesGroup):
    waiting_value = State()


class PaymentInfoStates(StatesGroup):
    waiting_info = State()


class BroadcastStates(StatesGroup):
    waiting_message = State()


class ViolationStates(StatesGroup):
    waiting_user_id = State()
    waiting_note = State()


class NewSectionStates(StatesGroup):
    """Admin /yangi_bolim buyrug'i orqali yangi bo'lim yaratishi."""
    title = State()
    tariff = State()


class GrantSubStates(StatesGroup):
    """Admin qo'lda obuna berishi / muddatini uzaytirishi."""
    waiting_user_id = State()
    waiting_tariff = State()
