import json
import logging
from mcp.server.fastmcp import FastMCP
from caldav.davclient import get_davclient
from datetime import datetime
import pytz
import re
from entities.calendar_info import CalendarEventInfo, CalendarTodoInfo

fastMCP=FastMCP("Calendar",port=20002)

client=None
def to_datetime(strDatetime:str,time_zone,format="%Y-%m-%dT%H:%M:%S"):
    """
    用来将大模型发送过来的字符串类型日期添加一个时区最后转为带时区的datetime
    :param strDatetime: 字符串类型日期
    :param time_zone: 时区（如"Asia/Shanghai"）
    :param format: 时间格式化字符串
    :return: datetime类型带时区的日期
    """
    if strDatetime=="":
        return None
    ori_time=datetime.strptime(strDatetime,format)
    tz=pytz.timezone(time_zone)
    tz_time=tz.localize(ori_time)
    return tz_time
def to_zone_datetime(date_time:datetime,time_zone):
    """
    直接为datetime类型的时间赋予时区
    :param date_time: 时间
    :param time_zone: 时区
    :return: 带时区的datetime
    """
    if type(date_time)=="datetime":
        tz=pytz.timezone(time_zone)
        tz_time=tz.localize(date_time)
        return tz_time
    else:
        return date_time
@fastMCP.tool("get_events")
async def get_events(start_time:str,end_time:str,time_zone:str="Asia/Shanghai"):
    """
    获取指定日期的日程（日期的格式是：2025-09-29T10:00:00），默认为东八区。支持修改时区。返回""表示没有日程。
    """
    logger.debug(f"请求查找开始时间：{start_time}，结束时间：{end_time}的日程，时区是：{time_zone}的日程")
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_datetime(start_time,time_zone)
    new_end_time=to_datetime(end_time,time_zone)
    for calendar in calendars:
        events = calendar.date_search(start=new_start_time, end=new_end_time)
        for event in events:
            start_time=to_zone_datetime(event.icalendar_component["DTSTART"].dt,time_zone)
            end_time = to_zone_datetime(event.icalendar_component["DTEND"].dt, time_zone)
            eventInfo=CalendarEventInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],start_time,end_time)
            logger.debug(f"已找到日程：{eventInfo.to_dict()}")
            events_result+=eventInfo.to_LLM()

    logger.debug( f"梳理完毕，内容为：\n{events_result}")
    return events_result
@fastMCP.tool("get_todos")
async def get_todo(start_time:str,end_time:str,done:str="NOT",time_zone:str="Asia/Shanghai"):
    """
    获取指定日期的待办事项（日期的格式是：2025-09-29T10:00:00），默认为东八区。支持修改时区。返回""表示没有待办事项。
    done参数如果为NOT，则只查找未完成的任务，如果为DONE则只查找已完成的任务，如果为ALL则查找所有任务。
    """
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_datetime(start_time,time_zone)
    new_end_time=to_datetime(end_time,time_zone)
    logger.debug( f"请求查找开始时间：{start_time}，结束时间：{end_time}的日程，时区为：{time_zone}，模式为：{done}的任务")
    try:
        for calendar in calendars:
            events = calendar.date_search(start=new_start_time, end=new_end_time,compfilter="VTODO")
            for event in events:
                start_time = to_zone_datetime(event.icalendar_component["DTSTART"].dt, time_zone)
                et=event.icalendar_component.get("DUE","")
                if et=="":
                    end_time=None
                else:
                    end_time = to_zone_datetime(et.dt, time_zone)
                eventInfo=CalendarTodoInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],start_time,end_time
                                           ,event.icalendar_component.get("PRIORITY",0))
                eventInfo.status=event.icalendar_instance.subcomponents[-1].get("STATUS","") if event.icalendar_component.get("STATUS","")=="" else event.icalendar_component.get("STATUS","")
                logger.debug(f"已找到任务：{eventInfo.to_dict()}")
                if done=='DONE':
                    if eventInfo.status=="COMPLETED":
                        events_result += eventInfo.to_LLM()
                    else:
                        continue
                elif done=='NOT':
                    if eventInfo.status=="COMPLETED":
                        continue
                    else:
                        events_result += eventInfo.to_LLM()
                elif done=='ALL':
                    events_result += eventInfo.to_LLM()
                else:
                    logger.error(f"参数done错误，传入：{done}，应为：DONE|NOT|ALL")
                    break
    except Exception as e:
        logger.error(f"获取待办事项失败：{e}")
        return f"获取待办事项失败，其他异常。{e}"
    logger.debug( f"梳理完毕，内容为：\n{events_result}")
    return events_result
@fastMCP.tool("create_event")
async def creat_event(calendar_name:str,name:str,start_time:str,end_time:str,location:str="",time_zone:str="Asia/Shanghai"):
    """
    创建日程（日期的格式是：2025-09-29T10:00:00），默认为东八区。支持修改时区
    """
    logger.debug(f"请求查找开始时间：{start_time}，结束时间：{end_time}的日程，时区为：{time_zone}，地点为：{location}，日历名为：{calendar_name}的日程")
    principal = client.principal()
    calendars = principal.calendars()
    new_start_time=to_datetime(start_time,time_zone)
    new_end_time=to_datetime(end_time,time_zone)
    calendar=None
    try:
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
    except Exception as e:
        logger.error(f"创建日程失败：{e}")
        return "创建日程失败，其他异常。"
# @fastMCP.tool("create_events")
# async def creat_events(events:str,time_zone:str="Asia/Shanghai"):
#     """
#     创建多个日程（日期的格式是：2025-09-29T10:00:00），默认为东八区。支持修改时区。
#     输入样例（必须按照顺序设定name,start,end,cn），cn为日历名，多个日程之间用换行(\n)分隔：
#     name=吃午饭,start=2025-09-29T10:00:00,end=2025-09-29T10:15:00,cn=个人日历
#     name=打游戏,start=2025-09-29T12:00:00,end=2025-09-29T14:15:00,cn=个人日历
#     """
#     principal = client.principal()
#     calendars = principal.calendars()
#     # 先获取整个日程列表中用到的日历有哪些
#     logger.debug("搜索日历中...")
#     event_dicts=[]
#     success=[]
#     fail=[]
#
#     event_list=events.split("\n")
#     for event in event_list:
#         event_dict={s.split("=")[0]:s.split("=")[1] for s in event.split(",")}
#         event_dicts.append(event_dict)
#     # for event in event_list:
#         # 处理日历不存在的情况
#         # ed = json.loads(event)
#         # ed["start_time"] = to_datetime(ed["start_time"])
#         # ed["end_time"] = to_datetime(ed["end_time"])
#         # ee = CalendarEventInfo.from_dic(ed)
#         # if ee.calendar_name not in calendar_names:
#         #     ee.calendar_name=calendars[0].get_display_name()
#         # calendar=calendar_names[ee.calendar_name]
#         # ce=calendar.save_event(summary=ee.name,dtstart=ee.start_time,dtend=ee.end_time)
#         # if ce!=None:
#         #     logger.debug(f"将日程{ee.name}添加到日历{calendar.get_display_name()}成功")
#         #     success.append(ee)
#         # else:
#         #     logger.debug(f"将日程{ee.name}添加到日历{calendar.get_display_name()}失败")
#         #     fail.append(ee)
#     for ed in event_dicts:
#         name=ed["name"]
#         start=to_datetime(ed["start"],time_zone)
#         end=to_datetime(ed["end"],time_zone)
#         calendar_name=ed["cn"]
#         for c in calendars:
#             if re.match(f"(.*){calendar_name}(.*)",c.get_display_name()):
#                 c.save_event(summary=name,dtstart=start,dtend=end)
#                 success.append(name)
#                 break
#         else:
#             logger.debug(f"未找到日历：{calendar_name}")
#             fail.append(name)
#     return f"""成功添加{len(success)}个日程，失败{len(fail)}个日程
#     以下日程成功：{[i for i in success]}
#     以下日程失败：{[i for i in fail]}
#     """


@fastMCP.tool("create_todo")
async def creat_todo(calendar_name:str,name:str,start_time:str,end_time:str,priority:int=0,time_zone:str="Asia/Shanghai"):
    """
    创建任务（日期的格式是：2025-09-29T10:00:00），默认为东八区。支持修改时区
    """
    logger.debug(f"请求创建开始时间：{start_time}，结束时间：{end_time}的日程，时区为：{time_zone}，日历名为：{calendar_name}的任务")
    principal = client.principal()
    calendars = principal.calendars()
    new_start_time=to_datetime(start_time,time_zone)
    new_end_time=to_datetime(end_time,time_zone)
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


# @fastMCP.tool("create_todos")
# async def creat_todos(todos: str,time_zone: str = "Asia/Shanghai"):
#     """
#     创建多个任务（日期的格式是：2025-09-29T10:00:00），默认为东八区。支持修改时区。
#     输入样例（必须按照顺序设定name,start,end,cn），cn为日历名，多个日程之间用换行(\n)分隔：
#     name=吃午饭,start=2025-09-29T10:00:00,end=2025-09-29T10:15:00,cn=个人日历,pr=0
#     name=打游戏,start=2025-09-29T12:00:00,end=2025-09-29T14:15:00,cn=个人日历,pr=1
#     """
#     principal = client.principal()
#     calendars = principal.calendars()
#     # 先获取整个日程列表中用到的日历有哪些
#     logger.debug("搜索日历中...")
#     todo_dicts=[]
#     success = []
#     fail = []
#     todo_list = todos.split("\n")
#     for todo in todo_list:
#         todo_dict = {s.split("=")[0]: s.split("=")[1] for s in todo.split(",")}
#         todo_dicts.append(todo_dict)
#     # for t in todos:
#     #     # 处理日历不存在的情况
#     #     td = json.loads(t)
#     #     td["start_time"] = to_datetime(td["start_time"])
#     #     td["end_time"] = to_datetime(td["end_time"])
#     #     tt = CalendarTodoInfo.from_dic(td)
#     #     if tt.calendar_name not in calendar_names:
#     #         tt.calendar_name = calendars[0].get_display_name()
#     #     calendar = calendar_names[tt.calendar_name]
#     #     ct = calendar.save_todo(summary=tt.name, dtstart=tt.start_time, due=tt.end_time,priority=td["priority"])
#     #     if ct != None:
#     #         logger.debug(f"将任务{tt.name}添加到日历{calendar.get_display_name()}成功")
#     #         success.append(ct)
#     #     else:
#     #         logger.debug(f"将任务{tt.name}添加到日历{calendar.get_display_name()}失败")
#     #         fail.append(ct)
#     for td in todo_dicts:
#         name=td["name"]
#         start=to_datetime(td["start"],time_zone)
#         end=to_datetime(td["end"],time_zone)
#         calendar_name=td["cn"]
#         pr=td["pr"]
#         for c in calendars:
#             if re.match(f"(.*){calendar_name}(.*)",c.get_display_name()):
#                 c.save_todo(summary=name,dtstart=start,due=end,priority=pr)
#                 success.append(name)
#                 break
#         else:
#             logger.debug(f"未找到日历：{calendar_name}")
#             fail.append(name)
#     return f"""成功添加{len(success)}个任务，失败{len(fail)}个任务
#     以下任务成功：{[i for i in success]}
#     以下任务失败：{[i for i in fail]}
#     """
@fastMCP.tool("list_calendars")
async def list_calendars():
    """
    获取所有日历
    :return: 日历名
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

if __name__ == "__main__":
    logger = logging.getLogger()
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
