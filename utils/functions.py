import re
from datetime import datetime
from functools import singledispatch
from typing import List, Dict
from xmlrpc.client import DateTime

import pytz
from multipledispatch import dispatch

from entities.exceptions import TimeZoneInfoError, ItemNumberException
from main import logger


@dispatch(str,str)
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
@dispatch(datetime,str)
def to_zone_datetime(date_time,time_zone):
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
    :return: 分类后的字典，键为时区，值为对应数据列表
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
                    time_zone_time=to_zone_datetime(v, time_zones[str(special_time_zone[i])])
                    new_times.append(time_zone_time)
                else:
                    time_zone_time=to_zone_datetime(v, other_time_zone)
                    new_times.append(time_zone_time)
            return new_times
        else:
            special_time_zone = list(time_zones.keys())
            for i, v in enumerate(data):
                if i in special_time_zone:
                    time_zone_time = to_zone_datetime(v, time_zones[str(special_time_zone[i])])
                    new_times.append(time_zone_time)
            return new_times
    except Exception as e:
        logger.error(e)
        raise e
def time_zone_splits_text(time_zones:Dict,data:List[str]|List[None])->List[str]:
    """
    将数据根据时区分类，返回字符串类型
    :param time_zones: 时区字典
    :param data: 数据列表
    :return: 分类后的字典，键为时区，值为对应数据列表
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
        logger.error(e)
        raise e
        return []
