from typing import List, Dict

from caldav import Calendar, Todo
from fastmcp import FastMCP
from loguru import logger

from apis import client
from entities.calendar_info import CalendarTodoInfo
from utils.functions import to_zone_datetime, time_zone_check, data_check, find_calendar, time_zone_splits, \
    datetime_to_zone_datetime, find_events, alarm_time_splits, time_calc

todo_mcp=FastMCP("todo")
@todo_mcp.tool("get_todos")
@logger.catch()
async def get_todo(start_time:str,end_time:str,done:str="NOT",time_zone:str="Asia/Shanghai"):
    """
    （需要先调用get_current_time工具获取当前时间。）
    获取指定日期的待办事项。从start_time~end_time。
    """
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_zone_datetime(start_time,time_zone)
    new_end_time=to_zone_datetime(end_time,time_zone)
    logger.debug( f"请求查找开始时间：{start_time}，结束时间：{end_time}的待办，时区为：{time_zone}，模式为：{done}的任务")
    try:
        for calendar in calendars:
            events = calendar.search(comp_class=Todo,start=new_start_time, end=new_end_time)

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
                                           ,event.icalendar_component.get("PRIORITY",0),event.icalendar_component.get("LOCATION",""))
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
@todo_mcp.tool("get_no_time_todos")
@logger.catch()
async def get_no_time_todos(done:str="NOT"):
    """
        获取无开始时间的任务，如果只要查找已完成的任务，done参数设为DONE。如果查找所有任务（完成和未完成）的，done参数设为ALL。
    """
    principal = client.principal()
    calendars = principal.calendars()
    events_result = """"""
    logger.debug(f"请求查找无开始时间的待办，模式为：{done}的任务")
    try:
        for calendar in calendars:
            events = calendar.date_search(start=None, compfilter="VTODO")
            for event in events:
                st_time=event.icalendar_component.get("DTSTART","")
                if st_time!="":
                    continue
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




@todo_mcp.tool("create_todos")
@logger.catch()
async def creat_todos(calendar_name:str, names:List[str], start_times:List[str],
                      end_times:List[str]=[],priority:List[int]=[],
                      time_zones:Dict[str,str]={"all":"Asia/Shanghai"},
                      remind_times:Dict[str,str]={"all":"-15m"},
                      positions:List[str]=[]):
    """
    （需要先调用get_current_time工具获取当前时间。）
    创建多个任务（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区
    不允许创建无时间任务。
    使用字典设置每个事件的时区，例如：{'2': 'Asia/Tokyo', 'other': 'Asia/Shanghai'}，特殊键有"all"和"other"，
    all用来约定所有事件的时区。other则表示在其他事件的时区。
    提醒默认开始前15分钟，使用字典设置每个事件的提醒时间，例如：{'2': '-15m', 'other': '-15m'}。与时区一样也有all键。
    """
    time_zone_check(time_zones, names)
    if priority==[]:
        priority=[0]*len(names)
    if positions==[]:
        positions=[""]*len(names)
    if start_times==[]:
        logger.error("传入不规范，开始时间为空")
        return "传入不规范，开始时间为空"
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
        zoned_start_times = time_zone_splits(time_zones, start_times)
        if end_times!=[]:
            zoned_end_times = time_zone_splits(time_zones, end_times)
        else:
            zoned_end_times=None
        alarm_times=alarm_time_splits(remind_times,zoned_start_times)
        for i in range(len(names)):
            if None not in start_times and None not in end_times!=[]:
                calendar_info_list.append(
                    CalendarTodoInfo(calendar_name, names[i], zoned_start_times[i],
                                     zoned_end_times[i] if zoned_end_times is not None else None,
                                     priority[i], positions[i],[alarm_times[i]]))
            else:
                calendar_info_list.append(CalendarTodoInfo(calendar_name, names[i],
                                                           zoned_start_times[i] if zoned_start_times is not None else None,
                                                           zoned_end_times[i] if zoned_end_times is not None else None,
                                                           priority[i],positions[i],[alarm_times[i]]))

        # 开始写入日历
        for calendar_info in calendar_info_list:
            try:
                event = calendar.save_todo(summary=calendar_info.name, priority=calendar_info.priority,
                                           dtstart=calendar_info.start_time,
                                           due=calendar_info.end_time,
                                           location=calendar_info.location,
                                           alarm_trigger=calendar_info.alarm_time[0], alarm_action="DISPLAY")
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

@todo_mcp.tool("create_notime_todos")
@logger.catch()
async def create_notime_todos(calendar_name:str, names:List[str],priority:List[int]=[],positions:List[str]=[]):
    """
    （需要先调用get_current_time工具获取当前时间。）
    创建多个无时间的待办任务
    """
    if priority==[]:
        priority=[0]*len(names)
    if positions==[]:
        positions=[""]*len(names)
    principal = client.principal()
    calendars = principal.calendars()
    calendar = find_calendar(calendars, calendar_name)
    calendar_info_list = []
    success_info = "成功："
    fail_info = "失败："
    if calendar != None:
        # 处理所有日程时区一致的情况
        for i in range(len(names)):
            calendar_info_list.append(
                CalendarTodoInfo(calendar_name,names[i], None,
                                 None,
                                 priority[i],positions[i],[]))

        # 开始写入日历
        for calendar_info in calendar_info_list:
            try:
                event = calendar.save_todo(summary=calendar_info.name, priority=calendar_info.priority,
                                           dtstart=calendar_info.start_time,
                                           due=calendar_info.end_time,
                                           location=calendar_info.location)
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
@todo_mcp.tool("create_noend_todos")
@logger.catch()
async def create_noend_todos(calendar_name:str,start_times:List[str], names:List[str],priority:List[int]=[],
                            remind_times:Dict[str,str]={"all":"-15m"},timezones:Dict[str,str]={"all":"Asia/Shanghai"},
                             positions:List[str]=""):
    """
    （需要先调用get_current_time工具获取当前时间。）
    创建多个无结束时间的待办任务
    使用字典设置每个事件的时区，例如：{'2': 'Asia/Tokyo', 'other': 'Asia/Shanghai'}，特殊键有"all"和"other"，
    all用来约定所有事件的时区。other则表示在其他事件的时区。
    提醒默认开始前15分钟，使用字典设置每个事件的提醒时间，例如：{'2': '-15m', 'other': '-15m'}。与时区一样也有all键。
    """

    if priority==[]:
        priority=[0]*len(names)
    if positions==[]:
        positions=[""]*len(names)
    if start_times!=None:
        data_check(names, start_times, priority)
        zoned_start_times = time_zone_splits(timezones, start_times)
    else:
        logger.error("参数传入错误，start_times不能为空")
        return "参数传入错误，start_times不能为空"

    zoned_remind_times=alarm_time_splits(remind_times,zoned_start_times)
    principal = client.principal()
    calendars = principal.calendars()
    calendar = find_calendar(calendars, calendar_name)
    calendar_info_list = []
    success_info = "成功："
    fail_info = "失败："
    if calendar != None:
        for i in range(len(names)):
            calendar_info_list.append(
                CalendarTodoInfo(calendar_name,names[i], zoned_start_times[i],
                                 None,
                                 priority[i],positions[i],zoned_remind_times))

        # 开始写入日历
        for calendar_info in calendar_info_list:
            try:
                event = calendar.save_todo(summary=calendar_info.name, priority=calendar_info.priority,
                                           dtstart=calendar_info.start_time,
                                           due=calendar_info.end_time,
                                           location=calendar_info.location,
                                           alarm_trigger=calendar_info.alarm_time[0], alarm_action="DISPLAY")
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

@todo_mcp.tool("edit_todo")
@logger.catch()
async def edit_todo(calendar_name:str, uid:str,new_name:str=None, start_time:str=None,
                    end_time:str=None, time_zone:str='Asia/Shanghai',
                    priority:int=-1,new_remind_time:str=None,position:str=""):
    """
    编辑待办
    （需要先调用get_something_with_uid工具获取事件UID。）
    编辑待办事项，根据日历名和事件UID（uid）找到事件后进行修改。不修改的内容置为null。
    """
    principal = client.principal()
    calendars=principal.calendars()
    calendar:Calendar=find_calendar(calendars, calendar_name)
    if calendar is None:
        logger.warning("没有找到对应日历")
        return "没有找到对应日历"
    elif calendar.name == calendar_name:
        try:
            event=calendar.todo_by_uid(uid)
            ori_delta=None
            if event.icalendar_component.has_key("DUE") and event.icalendar_component.has_key("DTSTART"):
                ori_delta=event.icalendar_component["DUE"].dt-event.icalendar_component["DTSTART"].dt
                if start_time==None:
                    new_start_time=datetime_to_zone_datetime(event.icalendar_component["DTSTART"].dt,time_zone)
                else:
                    new_start_time=to_zone_datetime(start_time, time_zone)
                if end_time==None:
                    new_end_time=datetime_to_zone_datetime(event.icalendar_component["DUE"].dt,time_zone)
                else:
                    new_end_time=to_zone_datetime(end_time, time_zone)
            else:
                new_start_time = to_zone_datetime(start_time, time_zone)
                new_end_time=to_zone_datetime(end_time, time_zone)
            if priority==-1:
                priority=event.icalendar_component["PRIORITY"]
            if priority>9 or priority<0:
                raise ValueError("优先级必须在0-9之间")
            if new_start_time!=None and new_end_time!=None and new_start_time>new_end_time:
                logger.warning(f"开始时间{new_start_time}晚于结束时间{new_end_time}")
                new_end_time=new_start_time+ori_delta
                logger.warning(f"调整结束时间为{new_end_time}")
            cal_event=CalendarTodoInfo(calendar_name,new_name if new_name!=None else event.icalendar_component["SUMMARY"],
                                        new_start_time,new_end_time,priority,position)
            ev=calendar.save_todo(uid=uid, summary=cal_event.name, dtstart=cal_event.start_time,
                                  due=cal_event.end_time, priority=cal_event.priority, alarm_trigger=new_remind_time,
                                  alarm_action="DISPLAY", location=cal_event.location)
            if ev is not None:
                logger.debug(f"修改成功：{cal_event.name}(优先级：{cal_event.priority}){cal_event.start_time}~{cal_event.end_time}")
                return "修改成功"
        except Exception as e:
            logger.error(f"修改错误，原因：{e}")
            return "修改失败，原因："+str(e)

@todo_mcp.tool("delete_todo")
@logger.catch()
async def delete_todo(calendar_name:str, uid:str):
    """
    （需要先调用get_something_with_uid工具获取待办UID和list_calendars获取日历名）
    删除待办，根据待办UID和日历名找到待办后进行删除。
    """
    principal = client.principal()
    calendars=principal.calendars()
    calendar:Calendar=find_calendar(calendars, calendar_name)
    if calendar is None:
        logger.warning("没有找到对应日历")
        return "没有找到对应日历"
    elif calendar.name == calendar_name:
        try:
            todo=calendar.todo_by_uid(uid)
            if todo:
                todo.delete()
                logger.debug(f"删除成功：{uid}")
                return "删除成功"
            else:
                logger.error(f"删除错误，原因：待办{uid}不存在")
                return "删除失败，原因：待办"+uid+"不存在"
        except Exception as e:
            logger.error(f"删除错误，原因：{e}")
            return "删除失败，原因："+str(e)
    else:
        logger.error(f"删除错误，原因：日历{calendar_name}不存在")
        return "删除失败，原因：日历"+calendar_name+"不存在"