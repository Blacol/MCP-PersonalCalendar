import json
import logging

from mcp.server.fastmcp import FastMCP
from caldav.davclient import get_davclient
from entities.calendar_info import CalendarEventInfo, CalendarTodoInfo
from utils.functions import *

fastMCP=FastMCP("Calendar",port=20002)

client=None



@fastMCP.tool("get_events")
async def get_events(start_time:str,end_time:str,time_zone:str="Asia/Shanghai"):
    """
    获取指定日期的日程（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区。返回""表示没有日程。
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
    获取指定日期的待办事项（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区。返回""表示没有待办事项。
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
@fastMCP.tool("create_events")
def create_events(calendar_name:str, names:List[str], start_times:List[str], end_times:List[str], locations:List[str]=None, time_zones:Dict={'all':"Asia/Shanghai"}):
    """
    创建多个日程（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区
    calendar_name:日历名。如果用户没有提及，询问用户，不要自己利用list_calendars工具进行查询。除非用户准许。
    names、start_times、end_times一一对应表示每一个日程的开始时间和结束时间。
    locations表示每一个日程的地点。与names一一对应。没有地点设为空字符串保存。
    time_zones表示每一个日程的时区。如果所有日程都是一个时区则使用{'all':"时区名"}，如果每一个日程时区不同，键表示names列表的索引，值为对应日程的时区。
    如果部分时区不同，相同的部分要给other键。
    例子1：
    用户：2025年1月1日9:00-10:00坐火车，地点：上海火车站、2025年1月1日11:00-12:00去A家，地点：X街3室、2025年1月3日9:00-12:00开会，时区：东京时间。
    以上日程加入我的日历中
    参数：
    {calendar_name:"我的日历",names:["坐火车","去A家","开会"],start_times:["2025-01-01T09:00","2025-01-01T11:00","2025-01-03T09:00"],
    end_times:["2025-01-01T10:00","2025-01-01T12:00","2025-01-03T12:00"],
    locations:["上海火车站","X街3室",""],
    time_zones:{"2":"Asia/Tokyo","other":"Asia/Shanghai"}
    }
    """
    time_zone_check(time_zones,names)
    data_check(names,start_times,end_times,locations)
    principal=client.principal()
    calendars=principal.calendars()
    calendar=find_calendar(calendars,calendar_name)
    calendar_info_list=[]
    success_info="成功："
    fail_info="失败："
    if calendar!=None:
        # 处理所有日程时区一致的情况
        if "all" in time_zones:
            for name,start_time,end_time,location in zip(names,start_times,end_times,locations):
                new_start_time=to_datetime(start_time,time_zones["all"])
                new_end_time=to_datetime(end_time,time_zones["all"])
                calendar_info=CalendarEventInfo(calendar.get_display_name(),name,new_start_time,new_end_time,location)
                calendar_info_list.append(calendar_info)
        # 处理部分一致情况
        elif "other" in time_zones:
            other_time_zone=time_zones["other"]
            del time_zones["other"]
            index=[int(i) for i in time_zones]
            for i,v in enumerate(zip(names,start_times,end_times,locations)):
                if i in index:
                    ii=index.index(i)
                    new_start_time=to_datetime(v[1],time_zones[str(i)])
                    new_end_time=to_datetime(v[2],time_zones[str(i)])
                    calendar_info=CalendarEventInfo(calendar.get_display_name(),v[0],new_start_time,new_end_time,v[3])
                    index.remove(i)
                else:
                    new_start_time=to_datetime(v[1],other_time_zone)
                    new_end_time=to_datetime(v[2],other_time_zone)
                    calendar_info=CalendarEventInfo(calendar.get_display_name(),v[0],new_start_time,new_end_time,v[3])
                calendar_info_list.append(calendar_info)
        # 处理所有日程时区全不一致的情况
        else:
            index = [int(i) for i in time_zones]
            for i, v in enumerate(zip(names, start_times, end_times, locations)):
                if i in index:
                    ii = index.index(i)
                    new_start_time = to_datetime(v[1], time_zones[str(i)])
                    new_end_time = to_datetime(v[2], time_zones[str(i)])
                    calendar_info = CalendarEventInfo(calendar.get_display_name(), v[0], new_start_time, new_end_time,
                                                      v[3])
                    index.remove(i)
                calendar_info_list.append(calendar_info)
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
async def creat_todos(calendar_name:str, names:List[str], start_times:List[str], end_times:List[str],priority:List[int],time_zones:Dict[str,str]={"all":"Asia/Shanghai"}):
    """
    创建多个任务（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区
    calendar_name:日历名。如果用户没有提及，询问用户，不要自己利用list_calendars工具进行查询。除非用户准许。
    names、start_times、end_times、priority一一对应表示任务的名字、开始时间、结束时间和优先级（未指定优先级的，优先级值为0）。
    time_zones表示每一个日程的时区。如果所有日程都是一个时区则使用{'all':"时区名"}，如果每一个日程时区不同，键表示names列表的索引，值为对应日程的时区。
    如果部分时区不同，相同的部分要给other键。
    例子1：
    用户：2025年1月1日9:00-10:00打卡、2025年1月1日11:00-12:00写代码、2025年1月3日9:00-12:00修改BUG，优先级：1，时区：东京时间。
    以上日程加入我的日历中
    参数：
    {calendar_name:"我的日历",names:["打卡","写代码","修改BUG"],start_times:["2025-01-01T09:00","2025-01-01T11:00","2025-01-03T09:00"],
    end_times:["2025-01-01T10:00","2025-01-01T12:00","2025-01-03T12:00"],
    priority:[0,0,1]
    time_zones:{"2":"Asia/Tokyo","other":"Asia/Shanghai"}
    }
    """
    time_zone_check(time_zones, names)
    data_check(names, start_times, end_times,priority)
    principal = client.principal()
    calendars = principal.calendars()
    calendar = find_calendar(calendars, calendar_name)
    calendar_info_list = []
    success_info = "成功："
    fail_info = "失败："
    if calendar != None:
        # 处理所有日程时区一致的情况
        if "all" in time_zones:
            for name, start_time, end_time, priority in zip(names, start_times, end_times, priority):
                new_start_time = to_datetime(start_time, time_zones["all"])
                new_end_time = to_datetime(end_time, time_zones["all"])
                calendar_info = CalendarTodoInfo(calendar.get_display_name(), name, new_start_time, new_end_time,
                                                  priority)
                calendar_info_list.append(calendar_info)
        # 处理部分一致情况
        elif "other" in time_zones:
            other_time_zone = time_zones["other"]
            del time_zones["other"]
            index = [int(i) for i in time_zones]
            for i, v in enumerate(zip(names, start_times, end_times, priority)):
                if i in index:
                    new_start_time = to_datetime(v[1], time_zones[str(i)])
                    new_end_time = to_datetime(v[2], time_zones[str(i)])
                    calendar_info = CalendarTodoInfo(calendar.get_display_name(), v[0], new_start_time, new_end_time,
                                                      v[3])
                    index.remove(i)
                else:
                    new_start_time = to_datetime(v[1], other_time_zone)
                    new_end_time = to_datetime(v[2], other_time_zone)
                    calendar_info = CalendarTodoInfo(calendar.get_display_name(), v[0], new_start_time, new_end_time,
                                                      v[3])
                calendar_info_list.append(calendar_info)
        # 处理所有日程时区全不一致的情况
        else:
            index = [int(i) for i in time_zones]
            for i, v in enumerate(zip(names, start_times, end_times, priority)):
                if i in index:
                    new_start_time = to_datetime(v[1], time_zones[str(i)])
                    new_end_time = to_datetime(v[2], time_zones[str(i)])
                    calendar_info = CalendarTodoInfo(calendar.get_display_name(), v[0], new_start_time, new_end_time,
                                                      v[3])
                    index.remove(i)
                calendar_info_list.append(calendar_info)
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
