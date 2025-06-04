
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters.callback_data import CallbackData
import calendar
from datetime import datetime

class SimpleCalCallbackFactory(CallbackData, prefix="simple_calendar"):
    act: str
    year: int
    month: int
    day: int

simple_cal_callback = SimpleCalCallbackFactory

class SimpleCalendar:
    def __init__(self, min_date: datetime = None, max_date: datetime = None, locale: str = "ru"):
        self.min_date = min_date
        self.max_date = max_date
        self.locale = locale

    async def start_calendar(self, year: int = datetime.now().year, month: int = datetime.now().month) -> InlineKeyboardMarkup:
        inline_kb = InlineKeyboardMarkup(row_width=7)
        ignore_callback = simple_cal_callback(act="IGNORE", year=year, month=month, day=0).pack()
        month_name = datetime(year, month, 1).strftime("%B")
        inline_kb.add(InlineKeyboardButton(f"{month_name} {str(year)}", callback_data=ignore_callback))

        # Weekdays
        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        inline_kb.row(*[InlineKeyboardButton(day, callback_data=ignore_callback) for day in week_days])

        # Calendar
        month_calendar = calendar.monthcalendar(year, month)
        for week in month_calendar:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(" ", callback_data=ignore_callback))
                    continue
                row.append(InlineKeyboardButton(
                    str(day),
                    callback_data=simple_cal_callback(act="DAY", year=year, month=month, day=day).pack()
                ))
            inline_kb.row(*row)

        # Navigation
        inline_kb.row(
            InlineKeyboardButton("<", callback_data=simple_cal_callback(act="PREV-MONTH", year=year, month=month, day=1).pack()),
            InlineKeyboardButton(" ", callback_data=ignore_callback),
            InlineKeyboardButton(">", callback_data=simple_cal_callback(act="NEXT-MONTH", year=year, month=month, day=1).pack())
        )

        return inline_kb

    async def process_selection(self, callback_query: CallbackQuery, callback_data: dict):
        action = callback_data["act"]
        year = int(callback_data["year"])
        month = int(callback_data["month"])
        day = int(callback_data["day"])

        if action == "IGNORE":
            await callback_query.answer()
            return False, None
        elif action == "DAY":
            return True, datetime(year, month, day)
        elif action in ["PREV-MONTH", "NEXT-MONTH"]:
            if action == "PREV-MONTH":
                month -= 1
                if month < 1:
                    month = 12
                    year -= 1
            else:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            new_kb = await self.start_calendar(year, month)
            await callback_query.message.edit_reply_markup(reply_markup=new_kb)
            return False, None
