import json
import logging
from typing import List
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
    获取指定日期的日程（日期的格式是：2025-09-29T10:00:00）
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
    获取指定日期的待办事项（日期的格式是：2025-09-29T10:00:00）
    :param start_time: 指定的开始日期
    :param end_time: 指定的结束日期
    :param done: True返回所有任务，False只返回未完成的任务，Done只返回已完成的任务
    :return: 待办信息（数值越高优先级越高）
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
            eventInfo=CalendarTodoInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],event.icalendar_component["DTSTART"].dt,event.icalendar_component.get("DUE","").dt
                                       ,event.icalendar_component.get("PRIORITY",0))
            eventInfo.status=event.icalendar_component.get("STATUS","")
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
    创建日程（日期的格式是：2025-09-29T10:00:00）
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
@fastMCP.tool("create_events")
async def creat_events(events:List[str]):
    """
    创建多个日程
    （所有日期的格式是：年（4位）-月（2位）-日（2位）T小时（2位）:分钟（2位）:秒（2位））

    CalendarEventInfo中的属性：
        name(str):日程名
        start_time(str)：开始时间
        end_time(str)：结束时间
        calendar_name(str)：所属日历

    参数例子：
    [
      "{\"name\": \"吃晚饭\", \"start_time\": \"2025-09-28T17:00:00\", \"end_time\": \"2025-09-28T18:00:00\", \"calendar_name\": \"个人日历\"}",
      "{\"name\": \"聚餐\", \"start_time\": \"2025-09-29T17:00:00\", \"end_time\": \"2025-09-29T18:00:00\", \"calendar_name\": \"工作日历\"}",
    ]
    :param events: 日程列表，是一个CalendarEventInfo类的对象JSON字符串，如果日程所属的日历不清晰，则统一添加到caldav中第一个日历中。
    :return: 完成状态
    """
    principal = client.principal()
    calendars = principal.calendars()
    # 先获取整个日程列表中用到的日历有哪些
    logger.debug("搜索日历中...")
    calendar_names={}
    success=[]
    fail=[]
    for event in events:
        # ee=json.loads(event, object_hook=CalendarEventInfo.from_dic)
        ed=json.loads(event)
        if ed["calendar_name"] not in calendar_names:
            calendar_names[ed["calendar_name"]]=None
    for cn in calendar_names:
        for c in calendars:
            if re.match(f"(.*){cn}(.*)",c.get_display_name()):
                calendar_names[cn]=c
                logger.debug("已经创建日历列表")
    for event in events:
        # 处理日历不存在的情况
        ed = json.loads(event)
        ed["start_time"] = to_datetime(ed["start_time"])
        ed["end_time"] = to_datetime(ed["end_time"])
        ee = CalendarEventInfo.from_dic(ed)
        if ee.calendar_name not in calendar_names:
            ee.calendar_name=calendars[0].get_display_name()
        calendar=calendar_names[ee.calendar_name]
        ce=calendar.save_event(summary=ee.name,dtstart=ee.start_time,dtend=ee.end_time)
        if ce!=None:
            logger.debug(f"将日程{ee.name}添加到日历{calendar.get_display_name()}成功")
            success.append(ee)
        else:
            logger.debug(f"将日程{ee.name}添加到日历{calendar.get_display_name()}失败")
            fail.append(ee)
    return f"""成功添加{len(success)}个日程，失败{len(fail)}个日程
    以下日程成功：{[i.name for i in success]}
    以下日程失败：{[i.name for i in fail]}
    """


@fastMCP.tool("create_todo")
async def creat_todo(calendar_name:str,name:str,start_time:str,end_time:str,priority:int=0):
    """
    创建日程
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


@fastMCP.tool("create_todos")
async def creat_todos(todos: List[str]):
    """
    创建多个任务
    参数例子：
    [
      "{\"name\": \"吃晚饭\", \"start_time\": \"2025-09-28T17:00:00\", \"end_time\": \"2025-09-28T18:00:00\", \"calendar_name\": \"个人日历\",\"priority\":0}",
      "{\"name\": \"聚餐\", \"start_time\": \"2025-09-29T17:00:00\", \"end_time\": \"2025-09-29T18:00:00\", \"calendar_name\": \"工作日历\",\"priority\":1}"
    ]
    :param todos: 日程列表，参考“参数例子”。如果日程所属的日历不清晰，则统一添加到caldav中第一个日历中。
    :return: 完成状态
    """
    principal = client.principal()
    calendars = principal.calendars()
    # 先获取整个日程列表中用到的日历有哪些
    logger.debug("搜索日历中...")
    calendar_names = {}
    success = []
    fail = []
    for todo in todos:
        # ee=json.loads(event, object_hook=CalendarEventInfo.from_dic)
        td = json.loads(todo)
        if td["calendar_name"] not in calendar_names:
            calendar_names[td["calendar_name"]] = None
    for cn in calendar_names:
        for c in calendars:
            if re.match(f"(.*){cn}(.*)", c.get_display_name()):
                calendar_names[cn] = c
                logger.debug("已经创建日历列表")
    for todo in todos:
        # 处理日历不存在的情况
        td = json.loads(todo)
        td["start_time"] = to_datetime(td["start_time"])
        td["end_time"] = to_datetime(td["end_time"])
        tt = CalendarTodoInfo.from_dic(td)
        if tt.calendar_name not in calendar_names:
            tt.calendar_name = calendars[0].get_display_name()
        calendar = calendar_names[tt.calendar_name]
        ct = calendar.save_todo(summary=tt.name, dtstart=tt.start_time, due=tt.end_time,priority=td["priority"])
        if ct != None:
            logger.debug(f"将任务{tt.name}添加到日历{calendar.get_display_name()}成功")
            success.append(ct)
        else:
            logger.debug(f"将任务{tt.name}添加到日历{calendar.get_display_name()}失败")
            fail.append(ct)
    return f"""成功添加{len(success)}个任务，失败{len(fail)}个任务
    以下任务成功：{[i.name for i in success]}
    以下任务失败：{[i.name for i in fail]}
    """
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
