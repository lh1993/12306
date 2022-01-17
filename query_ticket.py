#!/usr/bin/python
# -*- coding:utf-8 -*-

import requests
import ssl
import json
import re
import shelve
import time
import sys

reload(sys)
sys.setdefaultencoding('utf-8')

# 全局取消证书验证
ssl._create_default_https_context = ssl._create_unverified_context

# 只查询相关车次
TRAINS_30 = ['G2555', 'G113', 'G1085', 'G2571', 'G121', '181', 'G133', 'G219', 'G207', 'G2575', 'G2595', 'G2561', 'G1089', 'G149', 'G189']
TRAINS_31 = ['G2555', 'G113', 'G1085']


def GetToken():
    """微信获取Token"""
    CorpID = "**********"
    Secret = "****************"
    url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s" % (CorpID, Secret)
    res_data = requests.get(url)

    token = res_data.json()
    # print(token)
    return token['access_token']


def SendMessge(token, totag, agentid, data):
    """微信发消息"""
    url = "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token=%s" % token
    value = {
        "totag": totag,
        "msgtype": "text",
        "agentid": agentid,
        "text": {
            "content": data
        },
        "safe": 0
    }
    wdata = json.dumps(value).encode('utf-8')
    res_data = requests.post(url=url, data=wdata)
    return res_data.json()


def get_station_name():
    """获取火车站名称对应的代号"""
    station_link = "https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9044"
    res = requests.get(url=station_link)
    html = res.content
    # print(html)
    match = re.findall('\|([\x80-\xff]+)\|([A-Z]+)\|', html)
    db = shelve.open('StationName.dat')
    for station in match:
        db[station[0]] = station[1]
    db.close()


def get_ticket_list(date, fromstation, tostation):
    """余票查询"""
    db = shelve.open('StationName.dat')
    new_db = {v: k for k, v in db.items()}
    fromstation = db[fromstation]
    tostation = db[tostation]
    db.close()
    trains_list = []
    query_link = "https://kyfw.12306.cn/otn/leftTicket/queryA?leftTicketDTO.train_date=%s&leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s&purpose_codes=ADULT" % (date, fromstation, tostation)
    # Cookie实际为准
    headers = {
        'Accept': '*/*',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.79 Safari/537.36',
        'Cookie': 'BIGipServerotn=1089470986.38945.0000; RAIL_EXPIRATION=1644479329000; RAIL_DEVICEID=A2PtQAEDmto1f7sWMhWgLhXZb7zYgFKpSZo2hrfaQvzXcHGe_qoAs4xLkW-0cu-3V3Iuwl_SJVubyFUvGaf-cbQVX3pCkRF_2iKol1moXcBtosYi_h-kI5A4evw_TS0TX54W9Yc0aF3XLXRTjmAvZV-F2xh_S5Uj; guidesStatus=off; highContrastMode=defaltMode; cursorStatus=off; BIGipServerpool_passport=132383242.50215.0000'
    }
    # print(query_link)
    res = requests.get(url=query_link, headers=headers)
    html = res.json()

    ticket_list = html['data']['result']
    for i in ticket_list:
        tmp_list = i.split('|')
        # print(tmp_list)
        train_list = []
        # 车次
        train_list.append(tmp_list[3].decode('utf-8'))
        # 出发地
        train_list.append(new_db[tmp_list[6]].decode('utf-8'))
        # 目的地
        train_list.append(new_db[tmp_list[7]].decode('utf-8'))
        # 出发时间
        train_list.append(tmp_list[8])
        # 到达时间
        train_list.append(tmp_list[9])
        # 商务特等座
        train_list.append(tmp_list[32])
        # 一等座
        train_list.append(tmp_list[31])
        # 二等座
        train_list.append(tmp_list[30])
        # 高级软卧
        train_list.append(tmp_list[21])
        # 软卧
        train_list.append(tmp_list[23])
        # 动卧
        train_list.append(tmp_list[33])
        # 硬卧
        train_list.append(tmp_list[28])
        # 软座
        train_list.append(tmp_list[24])
        # 硬座
        train_list.append(tmp_list[29])
        # 无座
        train_list.append(tmp_list[26])
        trains_list.append(train_list)
        # print(train_list)

    return trains_list


def sendmessage(date, tickets):
    """获取有票的车次信息发送到微信"""
    for ticket in tickets:
        if date == '2022-01-30' and ticket[0] not in TRAINS_30:
            continue
        if date == '2022-01-31' and ticket[0] not in TRAINS_31:
            continue
        no_site = ticket[-1].encode('utf-8')
        site = ticket[-2].encode('utf-8')
        soft_site = ticket[-3].encode('utf-8')
        second_site = ticket[7].encode('utf-8')
        try:
            no_site = int(no_site)
        except ValueError:
            pass
        try:
            site = int(site)
        except ValueError:
            pass
        try:
            soft_site = int(soft_site)
        except ValueError:
            pass

        if no_site == "有" or site == "有" or soft_site == "有" or second_site == "有":
            train = ticket[0]
            leave_station = ticket[1]
            to_station = ticket[2]
            leave_time = ticket[3]
            to_time = ticket[4]
            second_site = ticket[7]
            soft_site = ticket[-3]
            site = ticket[-2]
            no_site = ticket[-1]
            print('车次: %s' % ticket[0])
            print('Tickets have a ticket ...')
        else:
            if isinstance(no_site, int) and no_site > 0:
                train = ticket[0]
                leave_station = ticket[1]
                to_station = ticket[2]
                leave_time = ticket[3]
                to_time = ticket[4]
                second_site = ticket[20]
                soft_site = ticket[-3]
                site = ticket[-2]
                no_site = ticket[-1]
                print('车次: %s' % ticket[0])
                print('Tickets have a ticket ...')
            elif isinstance(site, int) and site > 0:
                train = ticket[0]
                leave_station = ticket[1]
                to_station = ticket[2]
                leave_time = ticket[3]
                to_time = ticket[4]
                second_site = ticket[7]
                soft_site = ticket[-3]
                site = ticket[-2]
                no_site = ticket[-1]
                print('车次: %s' % ticket[0])
                print('Tickets have a ticket ...')
            elif isinstance(soft_site, int) and soft_site > 0:
                train = ticket[0]
                leave_station = ticket[1]
                to_station = ticket[2]
                leave_time = ticket[3]
                to_time = ticket[4]
                second_site = ticket[7]
                soft_site = ticket[-3]
                site = ticket[-2]
                no_site = ticket[-1]
                print('车次: %s' % ticket[0])
                print('Tickets have a ticket ...')
            elif isinstance(second_site, int) and second_site > 0:
                train = ticket[0]
                leave_station = ticket[1]
                to_station = ticket[2]
                leave_time = ticket[3]
                to_time = ticket[4]
                second_site = ticket[7]
                soft_site = ticket[-3]
                site = ticket[-2]
                no_site = ticket[-1]
                print('车次: %s' % ticket[0])
                print('Tickets have a ticket ...')
            else:
                print('车次: %s' % ticket[0])
                print('Tickets have been sold out ...')
                continue

        data = u'''
日期:{date}
车次: {train}
出发站:{leave_station}
到达站:{to_station}
出发时间:{leave_time}
到达时间:{to_time}
二等座：{second_site}
软座:{soft_site}
硬座:{site}
无座:{no_site}
'''.format(date=date, train=train, leave_station=leave_station, to_station=to_station, leave_time=leave_time,
           to_time=to_time, second_site = second_site, soft_site=soft_site, site=site, no_site=no_site)
        # print(data)

        token = GetToken()
        # print(token)
        # print(data)
        totag = "2"
        agentid = "3"
        SendMessge(token, totag, agentid, data)
        time.sleep(0.2)


if __name__ == '__main__':
    date_list = ['2002-01-30', '2002-01-31']
    fromstation = '北京'
    tostation = '上海'
    # 获取火车站名称对应的代号
    get_station_name()
    # 查询车票
    for date in date_list:
        print("# 日期: %s" % date)
        tickets = get_ticket_list(date, fromstation, tostation)
        # 过滤出有票的车次,发送消息到微信
        sendmessage(date, tickets)
