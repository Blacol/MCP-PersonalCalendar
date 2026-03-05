from datetime import datetime
from typing import List
from utils.functions import to_str_datetime

def alarm_text(alarm_time:List[datetime])->str:
    if alarm_time is None:
        return ""
    else:
        result=""
        for alarm in alarm_time:
            str_time=to_str_datetime(alarm,"%Y-%m-%d %H:%M")
            result+=str_time+","
        return result
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
    def __init__(self,calendar_name:str,name:str,start_time:datetime,end_time:datetime,location:str="",alarm_time:List=None):
        self.name=name
        self.start_time=start_time
        self.end_time=end_time
        self.calendar_name=calendar_name
        self.location=location
        self.alarm_time=alarm_time
    def to_dict(self):
        return {
            "calendar":self.calendar_name,
            "name":self.name,
            "start_time":self.start_time,
            "end_time":self.end_time,
            "location":self.location,
            "alarm_time":self.alarm_time
        }
    @staticmethod
    def from_dic(dic):
        return CalendarEventInfo(dic["calendar_name"],dic["name"],dic["start_time"],dic["end_time"],dic["location"],dic["alarm_time"])
    def to_LLM(self)->str:
        atext=alarm_text(self.alarm_time)
        return f"日历：{self.calendar_name}，日程：{self.name}\n时间：{self.start_time}~{self.end_time}\n地点：{self.location}\n于{atext}提醒\n"
class CalendarTodoInfo:
    """
    日历待办信息类
    属性:
        name(str): 待办名
        start_time(str)：开始时间
        end_time(str)：结束时间
        calendar_name(str)：所属日历的名字
        status(str)：任务状态
        priority(int)=0：优先级，值越高优先级越低
    """
    def __init__(self,calendar_name:str,name:str,start_time:datetime|None,end_time:datetime|None,priority:int=0,alarm_time:List=None):
        self.name=name
        self.start_time=start_time
        self.end_time=end_time
        self.calendar_name=calendar_name
        self.status=""
        self.priority=priority
        self.alarm_time=alarm_time

    def to_dict(self):
        return {
            "calendar":self.calendar_name,
            "name":self.name,
            "start_time":self.start_time,
            "end_time":self.end_time,
            "status":self.status,
            "priority":self.priority,
            "alarm_time":self.alarm_time
        }

    @staticmethod
    def from_dic(dic):
        return CalendarTodoInfo(dic["calendar_name"],dic["name"],dic["start_time"],dic["end_time"],dic["priority"],dic["alarm_time"])
    def to_LLM(self)->str:
        atext=alarm_text(self.alarm_time)
        return f"日历：{self.calendar_name}，待办：{self.name}\n时间：{self.start_time}~{self.end_time}\n状态：{self.status}\n优先级：{self.priority}\n于{atext}提醒\n"
