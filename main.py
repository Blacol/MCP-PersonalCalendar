import json
import logging

from caldav import Calendar
from caldav.elements.cdav import CalendarData
from mcp.server.fastmcp import FastMCP
from caldav.davclient import get_davclient
from mcp.server.fastmcp.prompts.base import Message

from entities.calendar_info import CalendarEventInfo, CalendarTodoInfo
from utils.functions import *
from loguru import logger
fastMCP=FastMCP("Calendar",port=20002)

client=None

@fastMCP.prompt("create_todos",description="创建待办事项")
def prompt_create_todos(calendar_name:str, names:str, start_times:str, end_times:str, locations:str, priority:str,time_zones:str)->Message:
    """
        创建待办事项提示词

        Args:
            calendar_name (str): 日历名称，指定要添加待办事项的日历
            names (str): 待办事项名称列表，JSON字符串格式，例如: '["任务1", "任务2"]'
            start_times (str): 开始时间列表，JSON字符串格式，例如: '["2025-01-01T09:00", "2025-01-02T10:00"]'
            end_times (str): 结束时间列表，JSON字符串格式，例如: '["2025-01-01T10:00", "2025-01-02T11:00"]'
            locations (str): 地点列表，JSON字符串格式，例如: '["办公室", "家里"]'
            priority (str): 优先级列表，JSON字符串格式，例如: '[1, 2]'，数字越大优先级越高
            time_zones (str): 时区列表，JSON字符串格式，例如: '["Asia/Shanghai", "Asia/Tokyo"]'
    """
    names=json.loads(names)
    start_times=json.loads(start_times)
    end_times=json.loads(end_times)
    locations=json.loads(locations)
    priority=json.loads(priority)
    time_zones=json.loads(time_zones)
    msg=f"向{calendar_name}添加待办事项："
    zoned_start_times=time_zone_splits_text(time_zones,start_times)
    zoned_end_times=time_zone_splits_text(time_zones,end_times)
    for i in range(len(names)):
        msg+=f"{names[i]}，"
        if zoned_start_times is not []:
            msg+=f"开始时间：{zoned_start_times[i]}"
        else:
            msg+=f"没有开始时间"
        if zoned_end_times is not []:
            msg += f"，结束时间：{zoned_end_times[i]}"
        else:
            msg+=f"，没有结束时间"
        if locations:
            msg+=f"\n地点：{locations[i]}"
        if priority:
            msg+=f"\n优先级：{priority[i]}"
        msg+="\n"
    return Message(msg,role="user")
@fastMCP.prompt("create_events",description="创建日程")
def prompt_create_events(calendar_name:str, names:str, start_times:str, end_times:str, locations:str, time_zones:str)->Message:
    """
        创建日程提示词

        Args:
            calendar_name (str): 日历名称，指定要添加待办事项的日历
            names (str): 待办事项名称列表，JSON字符串格式，例如: '["任务1", "任务2"]'
            start_times (str): 开始时间列表，JSON字符串格式，例如: '["2025-01-01T09:00", "2025-01-02T10:00"]'
            end_times (str): 结束时间列表，JSON字符串格式，例如: '["2025-01-01T10:00", "2025-01-02T11:00"]'
            locations (str): 地点列表，JSON字符串格式，例如: '["办公室", "家里"]'
            time_zones (str): 时区列表，JSON字符串格式，例如: '["Asia/Shanghai", "Asia/Tokyo"]'
    """
    logger.debug(f"开始生成提示词：{calendar_name},names:{names},start_times:{start_times},end_times:{end_times},time_zones:{time_zones}")
    names=json.loads(names)
    start_times=json.loads(start_times)
    end_times=json.loads(end_times)
    locations=json.loads(locations)
    time_zones=json.loads(time_zones)
    msg=f"向{calendar_name}添加日程："
    zoned_start_times=time_zone_splits_text(time_zones,start_times)
    zoned_end_times=time_zone_splits_text(time_zones,end_times)
    for i in range(len(names)):
        msg+=f"{names[i]}，"
        if zoned_start_times is not []:
            msg+=f"开始时间：{zoned_start_times[i]}"
        else:
            msg+=f"没有开始时间"
        if zoned_end_times is not []:
            msg += f"，结束时间：{zoned_end_times[i]}"
        else:
            msg+=f"，没有结束时间"
        if locations:
            msg+=f"\n地点：{locations[i]}"
        msg+="\n"
    logger.debug(f"生成的提示词为：{msg}")
    return Message(msg,role="user")

@fastMCP.tool("get_current_time")
async def get_current_time(time_zone:str="Asia/Shanghai"):
    """
    获取当前时间，默认为东八区。支持修改时区。
    """
    current_time=datetime_to_zone_datetime(datetime.now(),time_zone)
    return current_time.strftime("%Y-%m-%dT%H:%M")

@fastMCP.tool("get_events")
async def get_events(start_time:str,end_time:str,time_zone:str="Asia/Shanghai"):
    """
    获取指定日期的日程。
    Args:
        start_time (str): 开始时间，格式为：2025-09-29T10:00
        end_time (str): 结束时间，格式为：2025-09-29T10:00
        time_zone (str, optional): 时区，默认为东八区。
    """
    if start_time=="" or end_time=="":
        logging.warning("传入不规范，开始时间或结束时间为空")
        return "传入不规范，开始时间或结束时间为空"
    logger.debug(f"请求查找开始时间：{start_time}，结束时间：{end_time}的日程，时区是：{time_zone}的日程")
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_zone_datetime(start_time,time_zone)
    new_end_time=to_zone_datetime(end_time,time_zone)
    try:
        for calendar in calendars:
            events = calendar.date_search(start=new_start_time, end=new_end_time)
            for event in events:
                st=event.icalendar_component["DTSTART"].dt
                et=event.icalendar_component["DTEND"].dt
                eventInfo=CalendarEventInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],st,et)
                events_result+=eventInfo.to_LLM()
    except Exception as e:
        logger.error(f"获取日程时出错：{e}")
        return f"获取日程时出错：{e}"
    logger.debug( f"梳理完毕，内容为：\n{events_result}")
    return events_result
@fastMCP.tool("get_todos")
async def get_todo(start_time:str,end_time:str,done:str="NOT",time_zone:str="Asia/Shanghai"):
    """
    获取指定日期的待办事项
    Args:
        start_time (str): 开始时间，格式为：2025-09-29T10:00
        end_time (str): 结束时间，格式为：2025-09-29T10:00
        done (str, optional): 任务状态，默认为NOT。如果为DONE则只查找已完成的任务，如果为NOT则只查找未完成的任务，如果为ALL则查找所有任务。
        time_zone (str, optional): 时区，默认为东八区。
    """
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_zone_datetime(start_time,time_zone)
    new_end_time=to_zone_datetime(start_time,time_zone)
    logger.debug( f"请求查找开始时间：{start_time}，结束时间：{end_time}的待办，时区为：{time_zone}，模式为：{done}的任务")
    try:
        for calendar in calendars:
            events = calendar.comp_class(start=new_start_time, end=new_end_time,compfilter="VTODO")
            for event in events:
                st=event.icalendar_component.get("DTSTART","")
                if st=="":
                    st=None
                else:
                    st = st.dt
                et=event.icalendar_component.get("DUE","")
                if et=="":
                    et=None
                else:
                    et = et.dt
                eventInfo=CalendarTodoInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],st,et
                                           ,event.icalendar_component.get("PRIORITY",0))
                eventInfo.status=event.icalendar_instance.subcomponents[-1].get("STATUS","未开始") if event.icalendar_component.get("STATUS","")=="" else event.icalendar_component.get("STATUS","")
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
@fastMCP.tool("get_no_time_todos")
async def get_no_time_todos(done:str="NOT"):
    """
        获取无开始时间的任务
        Args:
            done (str, optional): 任务状态，默认为NOT。如果为DONE则只查找已完成的任务，如果为NOT则只查找未完成的任务，如果为ALL则查找所有任务。
    """
    principal = client.principal()
    calendars = principal.calendars()
    events_result = """"""
    logger.debug(f"请求查找无开始时间的待办，模式为：{done}的任务")
    try:
        for calendar in calendars:
            events = calendar.date_search(start=None, compfilter="VTODO")
            for event in events:
                eventInfo = CalendarTodoInfo(calendar.get_display_name(), event.icalendar_component["SUMMARY"],
                                             None, None
                                             , event.icalendar_component.get("PRIORITY", 0))
                eventInfo.status = event.icalendar_instance.subcomponents[-1].get("STATUS",
                                                                                  "") if event.icalendar_component.get(
                    "STATUS", "") == "" else event.icalendar_component.get("STATUS", "")
                logger.debug(f"已找到任务：{eventInfo.to_dict()}")
                if done == 'DONE':
                    if eventInfo.status == "COMPLETED":
                        events_result += eventInfo.to_LLM()
                    else:
                        continue
                elif done == 'NOT':
                    if eventInfo.status == "COMPLETED":
                        continue
                    else:
                        events_result += eventInfo.to_LLM()
                elif done == 'ALL':
                    events_result += eventInfo.to_LLM()
                else:
                    logger.error(f"参数done错误，传入：{done}，应为：DONE|NOT|ALL")
                    break
    except Exception as e:
        logger.error(f"获取待办事项失败：{e}")
        return f"获取待办事项失败，其他异常。{e}"
    logger.debug(f"梳理完毕，内容为：\n{events_result}")
    return events_result
@fastMCP.tool("create_events")
async def create_events(calendar_name:str, names:List[str], start_times:List[str], end_times:List[str], locations:List[str]=[], time_zones:Dict={'all':"Asia/Shanghai"}):
    """
    创建多个日程
    Args:
        calendar_name (str): 日历名称，指定要添加待办事项的日历
        names (List[str]): 日程名称列表，例如: ['坐火车', '去A家', '开会']
        start_times (List[str]): 开始时间列表，例如: ['2025-01-01T09:00', '2025-01-01T11:00', '2025-01-03T09:00']
        end_times (List[str]): 结束时间列表，例如: ['2025-01-01T10:00', '2025-01-01T12:00', '2025-01-03T12:00']
        locations (List[str], optional): 地点列表，例如: ['上海火车站', 'X街3室', '']
        time_zones (Dict[str,str], optional): 时区字典，例如: {'2': 'Asia/Tokyo', 'other': 'Asia/Shanghai'}
    """
    time_zone_check(time_zones,names)
    data_check(names,start_times,end_times)
    principal=client.principal()
    calendars=principal.calendars()
    calendar=find_calendar(calendars,calendar_name)
    calendar_info_list=[]
    success_info="成功："
    fail_info="失败："
    if not locations:
        locations=[""]*len(names)
    if calendar!=None:
        zoned_start_times=time_zone_splits(time_zones,start_times)
        zoned_end_times=time_zone_splits(time_zones,end_times)
        for i in range(len(names)):
            calendar_info_list.append(CalendarEventInfo(calendar_name,names[i],zoned_start_times[i],zoned_end_times[i],locations[i]))
        # 开始写入日历
        for calendar_info in calendar_info_list:
            try:
                event=calendar.save_event(summary=calendar_info.name,location=calendar_info.location,dtstart=calendar_info.start_time,dtend=calendar_info.end_time)
                if event is not None:
                    logger.debug(f"生成日程：{event.icalendar_component['SUMMARY']}，日历：{calendar.get_display_name()}成功")
                    success_info+=calendar_info.name+"\n"
            except Exception as e:
                logger.error(f"生成日程：{calendar_info.name}，日历：{calendar.get_display_name()}失败：{e}")
                fail_info+=calendar_info.name+"原因："+str(e)+"\n"
        # 返回结果
        return f"{success_info}\n{fail_info}"
    else:
        logger.debug(f"未找到日历：{calendar_name}")
        return "未找到日历"



@fastMCP.tool("create_todos")
async def creat_todos(calendar_name:str, names:List[str], start_times:List[str]=[], end_times:List[str]=[],priority:List[int]=[],time_zones:Dict[str,str]={"all":"Asia/Shanghai"}):
    """
    创建多个任务（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区
    Args:
        calendar_name (str): 日历名称，指定要添加待办事项的日历
        names (List[str]): 任务名称列表，例如: ['坐火车', '去A家', '开会']
        start_times (List[str], optional): 开始时间列表，例如: ['2025-01-01T09:00', '2025-01-01T11:00', '2025-01-03T09:00']
        end_times (List[str], optional): 结束时间列表，例如: ['2025-01-01T10:00', '2025-01-01T12:00', '2025-01-03T12:00']
        priority (List[int], optional): 优先级列表，例如: [1, 2, 0]，数字越大优先级越高
        time_zones (Dict[str,str], optional): 时区字典，例如: {'2': 'Asia/Tokyo', 'other': 'Asia/Shanghai'}

    """
    time_zone_check(time_zones, names)
    if priority==[]:
        priority=[0]*len(names)
    if start_times==[]:
        start_times=[None]*len(names)
    if end_times==[]:
        end_times=[None]*len(names)
    if start_times!=[] and end_times!=[]:
        data_check(names, start_times, end_times)
    elif start_times!=[] or end_times!=[]:
        data_check(names,start_times if start_times!=[] else end_times)

    principal = client.principal()
    calendars = principal.calendars()
    calendar = find_calendar(calendars, calendar_name)
    calendar_info_list = []
    success_info = "成功："
    fail_info = "失败："
    if calendar != None:
        # 处理所有日程时区一致的情况
        zoned_start_times = time_zone_splits(time_zones, start_times)
        zoned_end_times = time_zone_splits(time_zones, end_times)
        for i in range(len(names)):
            if None not in start_times and None not in end_times!=[]:
                calendar_info_list.append(
                    CalendarTodoInfo(calendar_name,names[i], zoned_start_times[i], zoned_end_times[i], priority[i]))
            else:
                calendar_info_list.append(CalendarTodoInfo(calendar_name,names[i],
                                                           zoned_start_times[i] if zoned_start_times!=[] else None,
                                                           zoned_end_times[i] if zoned_end_times!=[] else None,
                                                           priority[i]))

        # 开始写入日历
        for calendar_info in calendar_info_list:
            try:
                event = calendar.save_todo(summary=calendar_info.name, priority=calendar_info.priority,
                                            dtstart=calendar_info.start_time, due=calendar_info.end_time)
                if event is not None:
                    logger.debug(
                        f"生成任务：{event.icalendar_component['SUMMARY']}，日历：{calendar.get_display_name()}成功")
                    success_info += calendar_info.name + "\n"
            except Exception as e:
                logger.error(f"生成任务：{calendar_info.name}，日历：{calendar.get_display_name()}失败：{e}")
                fail_info += calendar_info.name + "原因：" + str(e) + "\n"
        # 返回结果
        return f"{success_info}\n{fail_info}"
    else:
        logger.debug(f"未找到日历：{calendar_name}")
        return "未找到日历"
@fastMCP.tool("get_something_with_uid")
async def get_something_with_uid(calendar_name:str, name:str, start_time:str,time_zone:str='Asia/Shanghai',isTodo:bool=False):
    """
    获取日程或待办（带UID）
    Args:
        calendar_name: 日历名
        name: 事件名
        start_time: 开始时间
        time_zone: 时区（默认'Asian/Shanghai'）
        isTodo: 是否是待办事项
    """

    principal = client.principal()
    calendars = principal.calendars()
    calendar: Calendar = find_calendar(calendars, calendar_name)

    if calendar is None:
        logger.warning("没有找到对应日历")
        return "没有找到对应日历"
    else:
        for cal in calendars:
            if cal.name == calendar_name:
                events = find_events(calendar, name, start_time, time_zone, isTodo)
                if len(events)==0:
                    return "没有事项或待办"
                return events
        return "没有对应日历"

@fastMCP.tool("edit_event")
async def edit_event(calendar_name:str, uid:str,new_name:str=None, start_time:str=None,end_time:str=None, location:str=None, time_zone:str='Asia/Shanghai'):
    """
    编辑日程
    Args:
        calendar_name (str): 日历名称，指定要编辑日程的日历
        uid (str): 日程UID
        new_name: 新的日程名字
        start_time (str): 新的开始时间，默认为None
        end_time (str): 新的结束时间，默认为None
        location (str): 新的地点，默认为None
        time_zone (str, optional): 新的时区，默认为None
    """
    principal = client.principal()
    calendars=principal.calendars()
    calendar:Calendar=find_calendar(calendars, calendar_name)
    for cal in calendars:
        if cal.name == calendar_name:
            try:

                event=calendar.event_by_uid(uid)
                if start_time==None:
                    new_start_time=datetime_to_zone_datetime(event.icalendar_component["DTSTART"].dt,time_zone)
                else:
                    new_start_time=to_zone_datetime(start_time, time_zone)
                if start_time==None:
                    new_end_time=datetime_to_zone_datetime(event.icalendar_component["DTEND"].dt,time_zone)
                else:
                    new_end_time=to_zone_datetime(end_time, time_zone)
                cal_event=CalendarEventInfo(calendar_name,new_name if new_name!=None else event.icalendar_component["SUMMARY"],
                                            new_start_time,new_end_time,location if location!=None else event.icalendar_component["LOCATION"])
                ev=calendar.save_event(summary=cal_event.name,dtstart=cal_event.start_time,dtend=cal_event.end_time,location=cal_event.location)
                if ev is not None:
                    logger.debug(f"修改成功：{cal_event.name}(于{cal_event.location}){cal_event.start_time}~{cal_event.end_time}")
            except Exception as e:
                logger.error(f"修改错误，原因：{e}")
@fastMCP.tool("edit_todo")
async def edit_todo(calendar_name:str, uid:str,new_name:str=None, start_time:str=None,end_time:str=None, location:str=None, time_zone:str='Asia/Shanghai'):
    """
    编辑待办
    Args:
        calendar_name (str): 日历名称，指定要编辑日程的日历
        uid (str): 待办UID
        new_name: 新的待办名字
        start_time (str): 新的开始时间，默认为None
        end_time (str): 新的结束时间，默认为None
        location (str): 新的地点，默认为None
        time_zone (str, optional): 新的时区，默认为None
    """
    principal = client.principal()
    calendars=principal.calendars()
    calendar:Calendar=find_calendar(calendars, calendar_name)
    for cal in calendars:
        if cal.name == calendar_name:
            try:

                event=calendar.event_by_uid(uid)
                if start_time==None:
                    new_start_time=datetime_to_zone_datetime(event.icalendar_component["DTSTART"].dt,time_zone)
                else:
                    new_start_time=to_zone_datetime(start_time, time_zone)
                if start_time==None:
                    new_end_time=datetime_to_zone_datetime(event.icalendar_component["DTEND"].dt,time_zone)
                else:
                    new_end_time=to_zone_datetime(end_time, time_zone)
                cal_event=CalendarEventInfo(calendar_name,new_name if new_name!=None else event.icalendar_component["SUMMARY"],
                                            new_start_time,new_end_time,location if location!=None else event.icalendar_component["LOCATION"])
                ev=calendar.save_event(summary=cal_event.name,dtstart=cal_event.start_time,dtend=cal_event.end_time,location=cal_event.location)
                if ev is not None:
                    logger.debug(f"修改成功：{cal_event.name}(于{cal_event.location}){cal_event.start_time}~{cal_event.end_time}")
            except Exception as e:
                logger.error(f"修改错误，原因：{e}")


@fastMCP.tool("list_calendars")
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

if __name__ == "__main__":
    # # 移除默认的日志处理器
    # logger.remove()
    # 添加文件日志处理器，记录DEBUG及以上级别的日志
    logger.add(f"./log/log-{datetime.strftime(datetime.now(), '%Y-%m-%d_%H-%M-%S')}.log", 
               rotation="2 days",
               level="DEBUG", 
               format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
               encoding="utf-8")
    # # 添加控制台日志处理器，只显示ERROR及以上级别的日志
    # logger.add(lambda msg: print(msg), level="DEBUG")
    
    config_JSON=json.loads(open("config.json","r",encoding="utf-8").read())

    client=get_davclient(username=config_JSON["calendar_username"],
                         password=config_JSON["calendar_password"],
                         url=config_JSON["calendar_url"])
    logger.debug("初始化完成")
    logger.debug("开始运行")
    fastMCP.settings.host = "0.0.0.0" # 服务器外部访问的允许地址
    fastMCP.run(transport="sse")