from datetime import datetime

from fastmcp import FastMCP
from loguru import logger

from apis import client
from utils.functions import datetime_to_zone_datetime

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