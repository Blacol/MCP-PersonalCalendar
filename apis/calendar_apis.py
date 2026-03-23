from datetime import datetime

from caldav import Calendar
from fastmcp import FastMCP
from loguru import logger

from apis import client
from utils.functions import datetime_to_zone_datetime, find_calendar, find_events

calendar_mcp=FastMCP("calendar")

@calendar_mcp.tool("get_current_time")
@logger.catch()
async def get_current_time(time_zone:str="Asia/Shanghai"):
    """
    获取当前时间，默认为东八区。支持修改时区。
    """
    current_time=datetime_to_zone_datetime(datetime.now(),time_zone)
    return current_time.strftime("%Y-%m-%dT%H:%M")



@calendar_mcp.tool("list_calendars")
@logger.catch()
async def list_calendars():
    """
    获取所有日历
    """
    try:
        principal = client.principal()
        calendars = principal.calendars()
        calendar_str=""
        for calendar in calendars:
            calendar_str+=calendar.get_display_name()+"\n"
        return f"找到了以下日历：\n{calendar_str}"
    except Exception as e:
        logger.debug(e)
        return "获取日历失败"

@calendar_mcp.tool("get_something_with_uid")
@logger.catch()
async def get_something_with_uid(calendar_name:str, name:str, query_time:str, time_zone:str= 'Asia/Shanghai', isTodo:bool=False):
    """
    获取特定时间的日程或待办（带UID）
    """

    principal = client.principal()
    calendars = principal.calendars()
    calendar: Calendar = find_calendar(calendars, calendar_name)
    if calendar is None:
        logger.warning("没有找到对应日历")
        return "没有找到对应日历"
    else:
        if calendar.name == calendar_name:
            events = find_events(calendar, name, query_time, time_zone, isTodo)
            if len(events)==0:
                return "没有事项或待办"
            return events
        return "没有对应日历"