import json
from datetime import datetime

from fastmcp import FastMCP
from loguru import logger
from mcp.server.fastmcp.prompts.base import Message

from apis.calendar_apis import calendar_mcp
from apis.event_apis import event_mcp
from apis.todo_apis import todo_mcp
from utils.functions import time_zone_splits_text

fastMCP=FastMCP("Calendar")
fastMCP.mount(event_mcp)
fastMCP.mount(todo_mcp)
fastMCP.mount(calendar_mcp)
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

    logger.debug("初始化完成")
    logger.debug("开始运行")
    fastMCP.run(transport="sse",port=20002,host="0.0.0.0")