import re
from copy import deepcopy
from datetime import datetime, timedelta
from typing import List, Dict

import pytz
from caldav import Todo, Event
from loguru import logger

from entities.exceptions import TimeZoneInfoError, ItemNumberException
def to_zone_datetime(strDatetime:str,time_zone:str,format="%Y-%m-%dT%H:%M"):
    """
    用来将大模型发送过来的字符串类型日期添加一个时区最后转为带时区的datetime
    :param strDatetime: 字符串类型日期
    :param time_zone: 时区（如"Asia/Shanghai"）
    :param format: 时间格式化字符串
    :return: datetime类型带时区的日期
    """
    if strDatetime=="":
        return None
    ori_time=datetime.strptime(strDatetime,format)
    tz=pytz.timezone(time_zone)
    tz_time=tz.localize(ori_time)
    return tz_time
def time_calc(time:datetime,num:int,unit:str):
    """
    对datetime类型的时间进行加减
    :param time: 时间
    :param num: 加减数
    :param unit: 单位，支持：'m（分钟）,h（小时）,d（天）,w（周）,mo（月）
    :return: 加减后的时间
    """
    if unit=="m":
        time_delta=timedelta(minutes=num)
        return time+time_delta
    elif unit=="h":
        time_delta = timedelta(hours=num)
        return time + time_delta
    elif unit=="d":
        time_delta = timedelta(days=num)
        return time + time_delta
    elif unit=="w":
        time_delta = timedelta(weeks=num)
        return time + time_delta
    elif unit=="mo":
        time_delta = timedelta(days=num*30)
        return time + time_delta
def datetime_to_zone_datetime(date_time,time_zone):
    """
    直接为datetime类型的时间赋予时区
    :param date_time: 时间
    :param time_zone: 时区
    :return: 带时区的datetime
    """
    if type(date_time)=="datetime":
        tz=pytz.timezone(time_zone)
        tz_time=tz.localize(date_time)
        return tz_time
    else:
        return date_time
def find_calendar(calendars:List,name:str):
    for calendar in calendars:
        if re.match(f"(.*){name}(.*)",calendar.get_display_name()):
            return calendar
    return None
@logger.catch
def find_events(calendar,name:str,start_time:str,zone:str="Asia/Shanghai",todo:bool=False):
    event_tuple=[]
    try:
        zone_start_time=to_zone_datetime(start_time,zone)
        if todo:
            events=calendar.search(comp_class=Todo,start=zone_start_time,summary=name)
        else:
            events = calendar.search(comp_class=Event,start=zone_start_time,summary=name)
        for event in events:
            current_name=str(event.icalendar_component["SUMMARY"])
            if re.match(f".*{name}.*",current_name)!=None:
                if todo:
                    event_tuple.append(
                        (current_name, str(event.icalendar_component["UID"]), event.icalendar_component["DTSTART"].dt if event.icalendar_component.get("DTSTART","")!="" else None,
                         event.icalendar_component["DUE"].dt if event.icalendar_component.get("DUE","")!="" else None))
                else:
                    event_tuple.append(
                        (current_name, str(event.icalendar_component["UID"]), event.icalendar_component["DTSTART"].dt,
                         event.icalendar_component["DTEND"].dt))
    except Exception as e:
        logger.error(f"查找事件失败，原因：{e}")
    # 整理成文字
    text=""""""
    for et in event_tuple:
        text+=f"{et[0]}({et[1]}) {et[2]}~{et[3]}\n"
    return text
def time_zone_check(time_zones:Dict,data:List):
    if "all" in time_zones.keys() and "other" in time_zones.keys():
        raise TimeZoneInfoError("时区设置错误，all和other无法同时出现。")
    elif "other" in time_zones.keys():
        keys=list(time_zones.keys())
        keys.remove("other")
        if len(keys)>=len(data):
            raise TimeZoneInfoError("时区设置错误，时区数量与数据数目不匹配。")
        elif len(keys)==0:
            raise TimeZoneInfoError("时区设置错误，不能只有other。")
    elif "all" in time_zones.keys():
        keys = list(time_zones.keys())
        keys.remove("all")
        if len(keys) !=0:
            raise TimeZoneInfoError("时区设置错误，时区数量与数据数目不匹配。")
def alarm_check(alarm_times:Dict,data:List):
    if "all" in alarm_times.keys() and "other" in alarm_times.keys():
        raise TimeZoneInfoError("提醒时间设置错误，all和other无法同时出现。")
    elif "other" in alarm_times.keys():
        keys=list(alarm_times.keys())
        keys.remove("other")
        if len(keys)>=len(data):
            raise TimeZoneInfoError("提醒时间设置错误，时区数量与数据数目不匹配。")
        elif len(keys)==0:
            raise TimeZoneInfoError("提醒时间设置错误，不能只有other。")
    elif "all" in alarm_times.keys():
        keys = list(alarm_times.keys())
        keys.remove("all")
        if len(keys) !=0:
            raise TimeZoneInfoError("提醒时间设置错误，提醒时间数量与数据数目不匹配。")
def data_check(a:List,*b:List):
    """
    检测一一对应数据的数量
    :param a: 时间名列表
    :param b: 待检测列表若干
    :exception ItemNumberException: 数据数量不匹配时报错。
    """
    len_lis=[len(l) for l in b]
    for l in len_lis:
        if len(a)!=l:
            raise ItemNumberException("数据数量不匹配")
def time_zone_splits(time_zones:Dict,data:List[str]|List[None])->List[datetime]:
    """
    将数据根据时区分类
    :param time_zones: 时区字典
    :param data: 数据列表
    :return: 分类后的数据列表
    """
    time_zones2=deepcopy(time_zones)
    try:
        if not data:
            return []
        if None in data:
            return []
        new_times=[]
        if "all" in time_zones2.keys():
            for d in data:
                time_zone_time=to_zone_datetime(d, time_zones2["all"])
                new_times.append(time_zone_time)
            return new_times
        elif "other" in time_zones2.keys():
            other_time_zone=time_zones2["other"]
            del time_zones2["other"]
            special_time_zone=list(time_zones2.keys())
            for i,v in enumerate(data):
                if str(i) in special_time_zone:
                    time_zone_time=to_zone_datetime(v, time_zones2[str(i)])
                    new_times.append(time_zone_time)
                else:
                    time_zone_time=to_zone_datetime(v, other_time_zone)
                    new_times.append(time_zone_time)
            return new_times
        else:
            special_time_zone = list(time_zones2.keys())
            for i, v in enumerate(data):
                if i in special_time_zone:
                    time_zone_time = to_zone_datetime(v, time_zones2[str(i)])
                    new_times.append(time_zone_time)
            return new_times
    except Exception as e:
        raise e
def alarm_time_splits(alarm_times:Dict, data: List[datetime] | List[None])->List[datetime]:
    """
    将数据根据提醒时间分类
    :param alarm_times: 提醒时间字典
    :param data: 开始时间列表
    :return: 分类后的已经计算好的时间。
    """
    alarm_times2=deepcopy(alarm_times)
    try:
        if not data:
            return []
        if None in data:
            return []
        remind_times=[]
        if "all" in alarm_times2:
            for d in range(len(data)):
                remind_times.append(alarm_times2["all"])
        elif "other" in alarm_times2:
            other_remind_time=alarm_times2["other"]
            del alarm_times2["other"]
            special_alarm=list(alarm_times2.keys())
            for i,v in enumerate(data):
                if str(i) in special_alarm:
                    remind_times.append(alarm_times2[str(i)])
                else:
                    remind_times.append(other_remind_time)
        new_times=[]
        for i,rt in enumerate(remind_times):
            time_unit=re.split("^([+-]\d+)(mo|m|h|d|w)$",rt)[1:3]
            time=time_calc(data[i],int(time_unit[0]),time_unit[1])
            new_times.append(time)
        return new_times
    except Exception as e:
        raise e
def time_zone_splits_text(time_zones:Dict,data:List[str]|List[None])->List[str]:
    """
    将数据根据时区分类，返回字符串类型
    :param time_zones: 时区字典
    :param data: 数据列表
    :return: 分类后的对应数据列表
    """
    try:
        if not data:
            return []
        if None in data:
            return []
        new_times=[]
        if "all" in time_zones.keys():
            for d in data:
                time_zone_time=to_zone_datetime(d, time_zones["all"])
                new_times.append(time_zone_time)
            return new_times
        elif "other" in time_zones.keys():
            other_time_zone=time_zones["other"]
            del time_zones["other"]
            special_time_zone=list(time_zones.keys())
            for i,v in enumerate(data):
                if i in special_time_zone:
                    time_zone=time_zones[str(special_time_zone[i])]
                    time_zone_time=to_zone_datetime(v, time_zone)
                    new_times.append(time_zone_time.strftime("%Y-%m-%dT%H:%M")+f"({time_zone})")
                else:
                    time_zone_time=to_zone_datetime(v, other_time_zone)
                    new_times.append(time_zone_time.strftime("%Y-%m-%dT%H:%M")+f"({other_time_zone})")
            return new_times
        else:
            special_time_zone = list(time_zones.keys())
            for i, v in enumerate(data):
                if i in special_time_zone:
                    time_zone=time_zones[str(special_time_zone[i])]
                    time_zone_time = to_zone_datetime(v, time_zone)
                    new_times.append(time_zone_time.strftime("%Y-%m-%dT%H:%M")+f"({time_zone})")
            return new_times
    except Exception as e:
        raise e
        return []
def to_str_datetime(dt:datetime,format:str="%Y-%m-%dT%H:%M")->str:
    """
    将datetime对象转换为字符串
    :param dt: datetime对象
    :param format: 字符串格式
    :return: 转换后的字符串
    """
    return dt.strftime(format)
