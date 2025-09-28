import json
import logging

import mcp.server.fastmcp.server
from icalendar.cal import Alarm
from mcp.server.fastmcp import FastMCP
from caldav.davclient import get_davclient
from datetime import datetime

import re

from entities.calendar_info import CalendarEventInfo, CalendarTodoInfo

fastMCP=FastMCP("Calendar")

client=None
def to_datetime(strDatetime:str,format="%Y-%m-%dT%H:%M:%S"):
    return datetime.strptime(strDatetime,format)
@fastMCP.tool("get_event")
async def get_events(start_time:str,end_time:str):
    """
    获取指定日期的日程
    （所有日期的格式是：年（4位）-月（2位）-日（2位）T小时（2位）:分钟（2位）:秒（2位））
    :param start_time: 指定的开始日期
    :end_time: 指定的结束日期
    :return: 日程信息
    """
    logger.debug(f"请求查找开始时间：{start_time}，结束时间：{end_time}的日程")
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_datetime(start_time)
    new_end_time=to_datetime(end_time)
    for calendar in calendars:
        events = calendar.date_search(start=new_start_time, end=new_end_time)
        print(events)
        for event in events:
            eventInfo=CalendarEventInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],event.icalendar_component["DTSTART"].dt,event.icalendar_component["DTEND"].dt)
            logger.debug(f"已找到日程：{eventInfo.to_dict()}")
            events_result+=eventInfo.to_LLM()

    logger.debug( f"梳理完毕，内容为：\n{events_result}")
    return events_result
@fastMCP.tool("get_todo")
async def get_todo(start_time:str,end_time:str,done:str="False"):
    """
    获取指定日期的待办事项
    （所有日期的格式是：年（4位）-月（2位）-日（2位）T小时（2位）:分钟（2位）:秒（2位））
    :param start_time: 指定的开始日期
    :end_time: 指定的结束日期
    :done: 是否返回已经完成的任务？True返回已完成和未完成的任务，False不返回已完成的任务只返回未完成的任务，Done只返回已完成的任务
    :return: 待办信息（优先级为0表示未设置。数值越高优先级越高）
    """
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_datetime(start_time)
    new_end_time=to_datetime(end_time)
    logger.debug( f"请求查找开始时间：{start_time}，结束时间：{end_time}的日程，模式为：{done}")
    for calendar in calendars:
        events = calendar.date_search(start=new_start_time, end=new_end_time,compfilter="VTODO")
        for event in events:
            eventInfo=CalendarTodoInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],event.icalendar_component["DTSTART"].dt,event.icalendar_component.get("DUE","").dt,
                                       event.icalendar_component.get("STATUS",""),event.icalendar_component["PRIORITY"])
            logger.debug(f"已找到任务：{eventInfo.to_dict()}")
            if done !='True' and done !='Done':
                if eventInfo.status=="COMPLETED":
                    continue
                else:
                    events_result += eventInfo.to_LLM()
            elif done=='Done':
                if eventInfo.status=="COMPLETED":
                    events_result += eventInfo.to_LLM()
            else:
                events_result += eventInfo.to_LLM()
    logger.debug( f"梳理完毕，内容为：\n{events_result}")
    return events_result
@fastMCP.tool("create_event")
async def creat_event(calendar_name:str,name:str,start_time:str,end_time:str,location:str=""):
    """
    创建日程
    （所有日期的格式是：年（4位）-月（2位）-日（2位）T小时（2位）:分钟（2位）:秒（2位））
    :param calendar_name: 指定的日历名称（模糊查询），用户未指定时询问用户保存到哪个日历里
    :param name: 日程名
    :param start_time: 日程开始时间
    :param end_time: 日程结束时间
    :param location: 日程地理位置
    :return: 完成状态
    """
    principal = client.principal()
    calendars = principal.calendars()
    new_start_time=to_datetime(start_time)
    new_end_time=to_datetime(end_time)
    calendar=None
    for c in calendars:
        if re.match(f"(.*){calendar_name}(.*)",c.get_display_name()):
            calendar=c
            break
    if calendar is None:
        logger.debug(f"未找到日历：{calendar_name}")
        return "未找到日历"
    else:
        event=calendar.save_event(summary=name,location=location,dtstart=new_start_time,dtend=new_end_time)
        logger.debug(f"生成日程：{event.icalendar_component['SUMMARY']}，日历：{calendar.get_display_name()}")
        if event!=None:
            logger.debug( f"将日程{name}添加到日历{calendar.get_display_name()}成功")
            return f"将日程{name}添加到日历{calendar.get_display_name()}成功"
        else:
            return "添加日程失败"
@fastMCP.tool("create_todo")
async def creat_todo(calendar_name:str,name:str,start_time:str,end_time:str,priority:int=0):
    """
    创建日程
    （所有日期的格式是：年（4位）-月（2位）-日（2位）T小时（2位）:分钟（2位）:秒（2位））
    :param calendar_name: 指定的日历名称（模糊查询），用户未指定时询问用户保存到哪个日历里
    :param name: 日程名
    :param start_time: 日程开始时间
    :param end_time: 日程结束时间
    :param priority: 优先级
    :return: 完成状态
    """
    principal = client.principal()
    calendars = principal.calendars()
    new_start_time=to_datetime(start_time)
    new_end_time=to_datetime(end_time)
    calendar=None
    for c in calendars:
        if re.match(f"(.*){calendar_name}(.*)",c.get_display_name()):
            calendar=c
            break
    if calendar is None:
        logger.debug(f"未找到日历：{calendar_name}")
        return "未找到日历"
    else:
        event=calendar.save_todo(summary=name,dtstart=new_start_time,due=new_end_time,priority= priority)
        logger.debug(f"生成待办：{event.icalendar_component['SUMMARY']}，日历：{calendar.get_display_name()}")
        if event!=None:
            logger.debug( f"将待办{name}添加到日历{calendar.get_display_name()}成功")
            return f"将待办{name}添加到日历{calendar.get_display_name()}成功"
        else:
            return "添加日程失败"
@fastMCP.tool("list_calendars")
async def list_calendars():
    """
    获取所有日历
    :return: 日历名
    """
    principal = client.principal()
    calendars = principal.calendars()
    calendar_str=""
    for calendar in calendars:
        calendar_str+=calendar.get_display_name()+"\n"
    return f"找到了以下日历：\n{calendar_str}"

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    fileHandler = logging.FileHandler("./log/log-" + datetime.strftime(datetime.now(), "%Y-%m-%d_%H-%M-%S") + ".log",encoding="utf-8")
    fileHandler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    fileHandler.setFormatter(formatter)
    logger.addHandler(fileHandler)
    config_JSON=json.loads(open("config.json","r",encoding="utf-8").read())

    client=get_davclient(username=config_JSON["calendar_username"],
                         password=config_JSON["calendar_password"],
                         url=config_JSON["calendar_url"])
    logger.debug("初始化完成")
    logger.debug("开始运行")
    fastMCP.settings.host = "0.0.0.0" # 服务器外部访问的允许地址
    fastMCP.run(transport="sse")
