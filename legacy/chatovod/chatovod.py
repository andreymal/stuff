#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import urllib2
import json

try:
    from simplexml import XML2Node
except:
    from xmpp.simplexml import XML2Node

class ChatovodError(Exception): pass

class Chat:
    def __init__(self, name):
        req = urllib2.urlopen("http://"+urllib2.quote(name)+".chatovod.ru/widget/")
        data = req.read()
        s = "var chatId = "
        f = data.find(s)
        if f <= 0: raise ChatovodError("chatId not found")
        data = data[f+len(s):f+len(s)+15]
        self.chatId = int(data[:data.find(";")])
        self.jd = json.JSONDecoder()
        self.name = name
        self.cookie = req.headers.get("set-cookie")
        self.cookie = self.cookie[self.cookie.find("sid="):]
        self.cookie = self.cookie[:self.cookie.find(";")+1]
        self.req = req
        
        self.user_cookies = {}
    
    def open(self, url="/ajax/", data=None, cookie=None):
        if not isinstance(url, urllib2.Request):
            if url[0] == "/": url = "http://" + urllib2.quote(self.name)+".chatovod.ru" + url
            url = urllib2.Request(url)
        url.add_header("cookie", cookie if not cookie is None else self.cookie)
        return urllib2.urlopen(url, data)
        #data = urllib2.urlopen(url, data).read()
        #return self.jd.decode(data)
    
    def listen(self, reload=0, cookie=None):
        #req = urllib2.Request("http://"+urllib2.quote(self.name)+".chatovod.ru/ajax/?act=listen&chat="+str(self.chatId)+"&reload="+("1" if reload else "0"))
        #req.add_header("cookie", cookie if cookie else self.cookie)
        data = self.open("/ajax/?act=listen&chat="+str(self.chatId)+"&reload="+("1" if reload else "0"), cookie=cookie).read()
        data = self.jd.decode(data)
        return data
        
    def login(self, user, password=None, captcha=None, cookie=""):
        query = "act=login&chat="+str(self.chatId)+"&"
        query += "msg=" + urllib2.quote(user) + "&"
        query += "pass=" + urllib2.quote(password if password else "") + "&"
        query += "remember=0&pv=0&"
        query += "c=" + (urllib2.quote(captcha) if captcha else "") + "&bind=0"
        
        req = self.open(data=query, cookie=cookie)
        data = self.jd.decode(req.read())
        if not cookie:
            cookie = req.headers.get("set-cookie")
            cookie = cookie[cookie.find("sid="):]
            cookie = cookie[:cookie.find(";")+1]
        if data['status'] == 'ok':
            self.user_cookies[unicode(user)] = cookie
        return cookie, data
    
    def getcaptcha(self, cookie=None):
        return self.open("/captcha/?ckey=", cookie=cookie).read()
    
    def send_action(self, user, act, **kwargs):
        cookie = self.user_cookies.get(user)
        if not cookie: return
        
        query = "act="+urllib2.quote(act)+"&chat="+str(self.chatId)
        for key, value in kwargs.items():
            if isinstance(key, unicode): key=key.encode("utf-8")
            if isinstance(value, unicode): value=value.encode("utf-8")
            query += "&" + urllib2.quote(key) + "=" + urllib2.quote(value)
        
        req = self.open(data=query, cookie=cookie)
        data = self.jd.decode(req.read())
        return data
        
    def leave(self, user):
        data=self.send_action(user, "leave")
        self.user_cookies.pop(unicode(user))
        return data
    
    def changestatus(self, user, status="ONLINE"):
        return self.send_action(user, "changestatus", status=status)
        
    def send_msg(self, user, msg, channel="main"):
        return self.send_action(user, "send", msg=msg, channel=channel)
        

if __name__ == "__main__":
    chat = Chat("ortherd")
    data = chat.listen(1)
    while 1:
        for key in data.keys():
            if key == "messages": continue
            print key
            for x in data[key]:
                print x
            print
            
        data = chat.listen()
        
def get_rooms_list(page=1):
    data = urllib2.urlopen("http://www.chatovod.ru/chats/?page="+str(int(page))).read()
    f=data.find('<table width="541" class="t">')
    if f <= 0: return []
    
    data = data[f:]
    data = data[:data.find("</table>")+8]
    
    node = XML2Node(data)
    del data
    
    chats = []
    for tr in node.getTags("tr"):
        if tr.getTag("th"): continue
        td1, td2 = tr.getTags("td")
        chats.append( (
            td1.getTag("a")['href'].encode("utf-8"),
            td1.getTag("a").getData(),
            int(td2.getData()),
        ) )
        
    return chats
