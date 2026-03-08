from typing import List, Dict

from caldav import Calendar, Todo
from fastmcp import FastMCP
from loguru import logger

from apis import client
from entities.calendar_info import CalendarTodoInfo
from utils.functions import to_zone_datetime, time_zone_check, data_check, find_calendar, time_zone_splits, \
    datetime_to_zone_datetime, find_events, alarm_time_splits

todo_mcp=FastMCP("todo")
@todo_mcp.tool("get_todos")
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
@todo_mcp.tool("get_no_time_todos")
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
async def creat_todos(calendar_name:str, names:List[str], start_times:List[str]=[],
                      end_times:List[str]=[],priority:List[int]=[],
                      time_zones:Dict[str,str]={"all":"Asia/Shanghai"},
                      remind_times:Dict[str,str]={"all":"-15m"}):
    """
    创建多个任务（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区
    Args:
        calendar_name (str): 日历名称，指定要添加待办事项的日历
        names (List[str]): 任务名称列表，例如: ['坐火车', '去A家', '开会']
        start_times (List[str], optional): 开始时间列表，例如: ['2025-01-01T09:00', '2025-01-01T11:00', '2025-01-03T09:00']
        end_times (List[str], optional): 结束时间列表，例如: ['2025-01-01T10:00', '2025-01-01T12:00', '2025-01-03T12:00']
        priority (List[int], optional): 优先级列表，例如: [1, 2, 0]，数字越大优先级越高
        time_zones (Dict[str,str], optional): 时区字典，例如: {'2': 'Asia/Tokyo', 'other': 'Asia/Shanghai'}
        remind_times (Dict[str,str], optional): 提醒时间字典，例如: {'2': '-15m', 'other': '-30m'}
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
        alarm_times=alarm_time_splits(remind_times,zoned_start_times)
        for i in range(len(names)):
            if None not in start_times and None not in end_times!=[]:
                calendar_info_list.append(
                    CalendarTodoInfo(calendar_name,names[i], zoned_start_times[i],
                                     zoned_end_times[i],
                                     priority[i],[alarm_times[i]]))
            else:
                calendar_info_list.append(CalendarTodoInfo(calendar_name,names[i],
                                                           zoned_start_times[i] if zoned_start_times!=[] else None,
                                                           zoned_end_times[i] if zoned_end_times!=[] else None,
                                                           priority[i],[alarm_times[i]]))

        # 开始写入日历
        for calendar_info in calendar_info_list:
            try:
                event = calendar.save_todo(summary=calendar_info.name, priority=calendar_info.priority,
                                            dtstart=calendar_info.start_time,
                                           due=calendar_info.end_time,
                                           alarm_trigger=calendar_info.alarm_time[0],alarm_action="DISPLAY")
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
@todo_mcp.tool("get_something_with_uid")
async def get_something_with_uid(calendar_name:str, name:str, query_time:str, time_zone:str= 'Asia/Shanghai', isTodo:bool=False):
    """
    获取日程或待办（带UID）
    Args:
        calendar_name: 日历名
        name: 事件名/待办名
        query_time: 查询时间，查询从这个时间开始及未来的日程或待办事项
        time_zone: 时区（默认'Asian/Shanghai'）
        isTodo: 是否是待办事项，默认为False，为True时只返回待办事项，为False时只返回日程
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


@todo_mcp.tool("edit_todo")
async def edit_todo(calendar_name:str, uid:str,new_name:str=None, start_time:str=None,end_time:str=None, location:str=None, time_zone:str='Asia/Shanghai',priority:int=-1):
    """
    编辑待办
    Args:
        calendar_name (str): 日历名称，指定要编辑待办的日历
        uid (str): 待办UID
        new_name: 新的待办名字，默认为None，None表示不修改，下同
        start_time (str): 新的开始时间，默认为None
        end_time (str): 新的结束时间，默认为None
        location (str): 新的地点，默认为None
        time_zone (str, optional): 新的时区，默认为None
        priority (int): 新的优先级，默认为-1，-1标识不修改，越高优先级越高
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
                                        new_start_time,new_end_time,priority)
            ev=calendar.save_todo(uid=uid,summary=cal_event.name,dtstart=cal_event.start_time,due=cal_event.end_time,priority=cal_event.priority)
            if ev is not None:
                logger.debug(f"修改成功：{cal_event.name}(优先级：{cal_event.priority}){cal_event.start_time}~{cal_event.end_time}")
                return "修改成功"
        except Exception as e:
            logger.error(f"修改错误，原因：{e}")
            return "修改失败，原因："+str(e)

@todo_mcp.tool("delete_todo")
async def delete_todo(calendar_name:str, uid:str):
    """
    删除待办
    Args:
        calendar_name (str): 日历名称，指定要删除待办的日历
        uid (str): 待办UID
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