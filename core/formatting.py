MS_IN_SECOND = 1000
SECONDS_IN_MINUTE = 60
MINUTES_IN_HOUR = 60


def format_ms(ms):
    return format_seconds(int(ms) // MS_IN_SECOND)


def format_seconds(seconds):
    seconds = int(seconds)
    return f"{seconds // SECONDS_IN_MINUTE}:{seconds % SECONDS_IN_MINUTE:02d}"


def format_hours_minutes(seconds):
    seconds = int(seconds)
    if 0 < seconds < SECONDS_IN_MINUTE:
        return f"{seconds} сек"
    total_minutes = seconds // SECONDS_IN_MINUTE
    hours, minutes = divmod(total_minutes, MINUTES_IN_HOUR)
    if hours:
        return f"{hours} ч {minutes} мин"
    return f"{minutes} мин"
