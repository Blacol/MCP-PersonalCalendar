import fastmcp
import json
from datetime import datetime

from fastmcp import FastMCP
from loguru import logger
from mcp.server.fastmcp.prompts.base import Message
import toml

from apis.calendar_apis import calendar_mcp
from apis.event_apis import event_mcp
from apis.todo_apis import todo_mcp
from utils.functions import time_zone_splits_text

with open("pyproject.toml", 'r', encoding="utf8") as f:
    project_info = toml.load(f)["project"]
    version = project_info["version"]
fastMCP=FastMCP("Calendar",version=version)
fastMCP.mount(event_mcp)
fastMCP.mount(todo_mcp)
fastMCP.mount(calendar_mcp)
client=None

if __name__ == "__main__":
    logger.debug("开始初始化")
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
    logger.debug(f"初始化完成，版本：{version}")
    logger.debug("开始运行")
    fastMCP.run(transport="sse",port=20002,host="0.0.0.0")