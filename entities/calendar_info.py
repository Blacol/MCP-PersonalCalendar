from datetime import datetime

from pydantic import BaseModel


class CalendarEventInfo:
    """
    日历日程信息类
    用于存储和管理日历事件的相关信息，包括事件的基本属性和操作方法。
    该类提供了事件信息的封装、访问和修改功能。
    属性:
        name(str):日程名
        start_time(datetime)：开始时间
        end_time(datetime)：结束时间
        calendar_name(str)：所属日历
    返回值:
        CalendarEventInfo实例对象
    """
    def __init__(self,calendar_name:str,name:str,start_time:datetime,end_time:datetime):
        self.name=name
        self.start_time=start_time
        self.end_time=end_time
        self.calendar_name=calendar_name
    def to_dict(self):
        return {
            "calendar":self.calendar_name,
            "name":self.name,
            "start_time":self.start_time,
            "end_time":self.end_time
        }
    @staticmethod
    def from_dic(dic):
        return CalendarEventInfo(dic["calendar_name"],dic["name"],dic["start_time"],dic["end_time"])
    def to_LLM(self)->str:
        return f"日历：{self.calendar_name}，日程：{self.name}\n时间：{self.start_time}~{self.end_time}\n"
class CalendarTodoInfo:
    """
    日历待办信息类
    属性:
        name(str): 待办名
        start_time(str)：开始时间
        end_time(str)：结束时间
        calendar_name(str)：所属日历的名字
        status(str)：任务状态
        priority(int)=0：优先级
    """
    def __init__(self,calendar_name:str,name:str,start_time:datetime,end_time:datetime,priority:int=0):
        self.name=name
        self.start_time=start_time
        self.end_time=end_time
        self.calendar_name=calendar_name
        self.status=""
        self.priority=priority
    def to_dict(self):
        return {
            "calendar":self.calendar_name,
            "name":self.name,
            "start_time":self.start_time,
            "end_time":self.end_time,
            "status":self.status,
            "priority":self.priority
        }

    @staticmethod
    def from_dic(dic):
        return CalendarTodoInfo(dic["calendar_name"],dic["name"],dic["start_time"],dic["end_time"],dic["priority"])
    def to_LLM(self)->str:
        return f"日历：{self.calendar_name}，待办：{self.name}\n时间：{self.start_time}~{self.end_time}\n状态：{self.status}\n优先级：{self.priority}\n"