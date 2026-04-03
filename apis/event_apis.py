import logging
from typing import List, Dict

from caldav import Calendar
from fastmcp import FastMCP
from loguru import logger

from apis import client, default_remind_time
from entities.calendar_info import CalendarEventInfo
from utils.functions import to_zone_datetime, time_zone_check, data_check, find_calendar, time_zone_splits, \
    datetime_to_zone_datetime, alarm_time_splits

event_mcp=FastMCP("event")

@event_mcp.tool("get_events")
@logger.catch()
async def get_events(start_time:str,end_time:str,time_zone:str="Asia/Shanghai"):
    """
    （需要先调用get_current_time工具获取当前时间。）
    获取指定日期的日程。从start_time~end_time。
    日期格式为：2025-09-29T10:00，默认东八区。
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
                eventInfo=CalendarEventInfo(calendar.get_display_name(),event.icalendar_component["SUMMARY"],st,et,
                                            event.icalendar_component.get("LOCATION",""))
                events_result+=eventInfo.to_LLM()
    except Exception as e:
        logger.error(f"获取日程时出错：{e}")
        return f"获取日程时出错：{e}"
    logger.debug( f"梳理完毕，内容为：\n{events_result}")
    return events_result
@event_mcp.tool("create_events")
@logger.catch()
async def create_events(calendar_name:str, names:List[str], start_times:List[str],
                        end_times:List[str], locations:List[str]=[],
                        time_zones:Dict={'all':"Asia/Shanghai"},remind:Dict={'all':default_remind_time}):
    """
    （需要先调用get_current_time工具获取当前时间。）
    创建多个日程。允许创建带提醒时间的日程。（仅能添加1个提醒器，多重提醒器请借助第三方软件完成。）
    时间格式：2025-09-29T10:00
    使用字典设置每个事件的时区，例如：{'2': 'Asia/Tokyo', 'other': 'Asia/Shanghai'}，特殊键有"all"和"other"，
    all用来约定所有事件的时区。other则表示在其他事件的时区。
    提醒默认开始前15分钟，使用字典设置每个事件的提醒时间，例如：{'2': '-15m', 'other': '-15m'}。与时区一样也有all键。
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
        alarm_times=alarm_time_splits(remind,zoned_start_times)
        for i in range(len(names)):
            calendar_info_list.append(CalendarEventInfo(calendar_name,names[i],zoned_start_times[i],zoned_end_times[i],locations[i],[alarm_times[i]]))
        # 开始写入日历
        for calendar_info in calendar_info_list:
            try:
                event=calendar.save_event(summary=calendar_info.name,location=calendar_info.location,dtstart=calendar_info.start_time,dtend=calendar_info.end_time,
                                          alarm_trigger=calendar_info.alarm_time[0],alarm_action="DISPLAY")
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
@event_mcp.tool("edit_event")
@logger.catch()
async def edit_event(calendar_name:str, uid:str,new_name:str=None, start_time:str=None,
                     end_time:str=None, location:str=None, time_zone:str='Asia/Shanghai',
                     new_remind_time:str=None):
    """
    （需要先调用get_something_with_uid工具获取事件UID。）
    编辑日程，根据日历名和事件UID（）找到事件后进行修改。不修改的内容置为null。
    """
    principal = client.principal()
    calendars=principal.calendars()
    calendar:Calendar=find_calendar(calendars, calendar_name)
    if calendar is None:
        logger.warning("没有找到对应日历")
        return "没有找到对应日历"
    elif calendar.name == calendar_name:
        try:

            event=calendar.event_by_uid(uid)
            ori_delta=event.icalendar_component["DTEND"].dt-event.icalendar_component["DTSTART"].dt
            if start_time==None:
                new_start_time=datetime_to_zone_datetime(event.icalendar_component["DTSTART"].dt,time_zone)
            else:
                new_start_time=to_zone_datetime(start_time, time_zone)
            if end_time==None:
                new_end_time=datetime_to_zone_datetime(event.icalendar_component["DTEND"].dt,time_zone)
            else:
                new_end_time=to_zone_datetime(end_time, time_zone)

            if new_start_time>new_end_time:
                logger.warning(f"开始时间{new_start_time}晚于结束时间{new_end_time}")
                new_end_time=new_start_time+ori_delta
                logger.warning(f"调整结束时间为{new_end_time}")
            cal_event=CalendarEventInfo(calendar_name,new_name if new_name!=None else event.icalendar_component["SUMMARY"],
                                        new_start_time,new_end_time,location if location!=None else event.icalendar_component["LOCATION"])
            ev=calendar.save_event(uid=uid,summary=cal_event.name,dtstart=cal_event.start_time,dtend=cal_event.end_time,
                                   location=cal_event.location,alarm_trigger=new_remind_time,
                                   alarm_action="DISPLAY")
            if ev is not None:
                logger.debug(f"修改成功：{cal_event.name}(于{cal_event.location}){cal_event.start_time}~{cal_event.end_time}")
                return "修改成功"
        except Exception as e:
            logger.error(f"修改错误，原因：{e}")
            return "修改失败，原因："+str(e)
@event_mcp.tool("delete_event")
@logger.catch()
async def delete_event(calendar_name:str, uid:str):
    """
    （需要先调用get_something_with_uid工具获取事件UID和list_calendars获取日历名）
    删除日程，根据事件UID和日历名找到事件后进行删除。
    """
    principal = client.principal()
    calendars=principal.calendars()
    calendar:Calendar=find_calendar(calendars, calendar_name)
    if calendar is None:
        logger.warning("没有找到对应日历")
        return "没有找到对应日历"
    elif calendar.name == calendar_name:
        try:
            event=calendar.event_by_uid(uid)
            if event:
                event.delete()
                logger.debug(f"删除成功：{uid}")
                return "删除成功"
            else:
                logger.error(f"删除错误，原因：日程{uid}不存在")
                return "删除失败，原因：日程"+uid+"不存在"
        except Exception as e:
            logger.error(f"删除错误，原因：{e}")
            return "删除失败，原因："+str(e)
    else:
        logger.error(f"删除错误，原因：日历{calendar_name}不存在")
        return "删除失败，原因：日历"+calendar_name+"不存在"