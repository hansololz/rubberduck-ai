from datetime import datetime

datetime_format = '%Y-%m-%d %H:%M:%S'


def get_datetime(timestamp: int) -> str:
  return datetime.fromtimestamp(timestamp).strftime(datetime_format)
