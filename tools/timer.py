import os
import requests
from datetime import datetime
import pytz
from pydantic import BaseModel, Field


class Tools:
    class Valves(BaseModel):
        CLOCK_BEDTIME_HOUR: int = Field(
            default=23,
            description="The hour when the AI should start nagging about bedtime.",
        )
        CLOCK_BEDTIME_MINUTE: int = Field(
            default=0,
            description="The minute when the AI should start nagging about bedtime.",
        )
        SLEEP_DURATION_HOURS: int = Field(
            default=8,
            description="The number of hours of sleep before the reminder stops.",
        )
        TIMEZONE: str = Field(
            default="UTC",
            description="The timezone to use for current time calculations.",
        )

    def __init__(self):
        self.valves = self.Valves()

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        :return: The current time.
        """
        timezone = pytz.timezone(self.valves.TIMEZONE)
        now = datetime.now(timezone)
        current_time = now.strftime("%H:%M:%S")
        current_date = now.strftime("%A, %B %d, %Y")

        current_hour = now.hour
        current_minute = now.minute

        bedtime_hour = self.valves.CLOCK_BEDTIME_HOUR
        bedtime_minute = self.valves.CLOCK_BEDTIME_MINUTE
        sleep_duration = self.valves.SLEEP_DURATION_HOURS

        bedtime = now.replace(
            hour=bedtime_hour, minute=bedtime_minute, second=0, microsecond=0
        )
        wake_up_time = bedtime + timedelta(hours=sleep_duration)

        result = f"Current Date is {current_date}, current time is {current_time}."

        if now >= bedtime and now <= wake_up_time:
            result += ". Remind the user to go to bed as it is already late."

        return result
