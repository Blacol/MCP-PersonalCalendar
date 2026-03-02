"""
MCP API包
所有API都在这里
"""
import json

from caldav.davclient import get_davclient

config_JSON=json.loads(open("config.json","r",encoding="utf-8").read())
client=get_davclient(username=config_JSON["calendar_username"],
                         password=config_JSON["calendar_password"],
                         url=config_JSON["calendar_url"])