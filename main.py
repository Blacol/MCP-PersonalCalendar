import json
import logging

from mcp.server.fastmcp import FastMCP
from caldav.davclient import get_davclient
from mcp.server.fastmcp.prompts.base import Message

from entities.calendar_info import CalendarEventInfo, CalendarTodoInfo
from utils.functions import *

fastMCP=FastMCP("Calendar",port=20002)

client=None
logger = logging.getLogger()
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
    return Message(msg,role="user")

@fastMCP.tool("get_current_time")
async def get_current_time(time_zone:str="Asia/Shanghai"):
    """
    获取当前时间，默认为东八区。支持修改时区。
    """
    current_time=to_zone_datetime(datetime.now(),time_zone)
    return current_time.strftime("%Y-%m-%dT%H:%M:%S")

@fastMCP.tool("get_events")
async def get_events(start_time:str,end_time:str,time_zone:str="Asia/Shanghai"):
    """
    获取指定日期的日程（日期的格式是：2025-09-29T10:00），默认为东八区。支持修改时区。返回""表示没有日程。
    """
    logger.debug(f"请求查找开始时间：{start_time}，结束时间：{end_time}的日程，时区是：{time_zone}的日程")
    principal=client.principal()
    calendars=principal.calendars()
    events_result=""""""
    new_start_time=to_zone_datetime(start_time,time_zone)
    new_end_time=to_zone_datetime(end_time,time_zone)
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
    new_start_time=to_zone_datetime(start_time,time_zone)
    new_end_time=to_zone_datetime(end_time,time_zone)
    logger.debug( f"请求查找开始时间：{start_time}，结束时间：{end_time}的待办，时区为：{time_zone}，模式为：{done}的任务")
    try:
        for calendar in calendars:
            events = calendar.date_search(start=new_start_time, end=new_end_time,compfilter="VTODO")
            for event in events:
                st=event.icalendar_component.get("DTSTART","")
                if st=="":
                    start_time=None
                else:
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
@fastMCP.tool("get_no_time_todos")
async def get_no_time_todos(done:str="NOT",time_zone:str="Asia/Shanghai"):
    """
        获取无开始时间的任务
        done参数如果为NOT，则只查找未完成的任务，如果为DONE则只查找已完成的任务，如果为ALL则查找所有任务。
    """
    principal = client.principal()
    calendars = principal.calendars()
    events_result = """"""
    logger.debug(f"请求查找无开始时间的待办，时区为：{time_zone}，模式为：{done}的任务")
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
def create_events(calendar_name:str, names:List[str], start_times:List[str], end_times:List[str], locations:List[str]=[], time_zones:Dict={'all':"Asia/Shanghai"}):
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
        new_start_time = None
        new_end_time = None
        
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

    logger.setLevel(logging.ERROR)
    fileHandler = logging.FileHandler("./log/log-" + datetime.strftime(datetime.now(), "%Y-%m-%d_%H-%M-%S") + ".log",encoding="utf-8")
    fileHandler.setLevel(logging.ERROR)
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
