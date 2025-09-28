from datetime import datetime
class CalendarEventInfo:
    """
    日历日程信息类
    """
    def __init__(self,calendar:str,name:str,start_time:datetime,end_time:datetime):
        self.name=name
        self.start_time=start_time
        self.end_time=end_time
        self.calendar_name=calendar
    def to_dict(self):
        return {
            "calendar":self.calendar_name,
            "name":self.name,
            "start_time":self.start_time,
            "end_time":self.end_time
        }
    def to_LLM(self)->str:
        return f"日历：{self.calendar_name}，日程：{self.name}\n时间：{self.start_time}~{self.end_time}\n"
class CalendarTodoInfo:
    """
    日历待办信息类
    """
    def __init__(self,calendar:str,name:str,start_time:datetime,end_time:datetime,status:str,priority:int=0):
        self.name=name
        self.start_time=start_time
        self.end_time=end_time
        self.calendar_name=calendar
        self.status=status
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
    def to_LLM(self)->str:
        return f"日历：{self.calendar_name}，待办：{self.name}\n时间：{self.start_time}~{self.end_time}\n状态：{self.status}\n优先级：{self.priority}\n"