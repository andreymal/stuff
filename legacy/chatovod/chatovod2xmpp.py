#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import socket
import time
import random
import traceback
from hashlib import sha1
from base64 import b64encode, b64decode
from threading import RLock, Thread
from urllib2 import unquote, quote, urlopen

import chatovod
from pyjabberd_utilites import load_config, node_reader, jid_split, gen_error, gen_iq_result, gen_stream_stream, Node, XML2Node

class CExc(Exception): pass
class NodeProcessed(Exception): pass

host = None # init after connecting
sock = None
lock = RLock() # for socket
reader = None

deletechars="".join(chr(x) for x in range(32) if x not in (10, 13))

rooms_list = []
rooms_list_dict = {}
rooms_list_time = 0

rooms = {} # jabber

config = {
    'host': 'localhost',
    'server': '',
    'transport_host': 'chatovod.localhost',
    'port': '52220',
    'password': 'secret'
}

smile_cache = {}

def get_smile(url):
    data = smile_cache.get(url)
    if data: return data
    try: data = urlopen(url).read()
    except: return url
    else:
        typ = url[-4:].lower()
        if typ == ".gif": typ = "image/gif"
        elif typ in (".jpg", ".jpeg"): typ = 'image/jpeg'
        else: typ = 'image/png'
        smile_cache[url] = "data:" + typ + ";base64," + quote(b64encode(data))
        return smile_cache[url]

class Room:
    def __init__(self, name):
        name = name.lower()
        self.name = name
        self.chat = chatovod.Chat(name)
        self.clients = {} # jabber
        self.chat_users = {} # chatovod
        self.last20 = []
        self.stopped = False
        self.topic = None
        #self.cookie = {} # joined from jabber
        
        self.clients_timeout = time.time()
        
        self.captcha_cache = {}
        self.msg_id_cache = {}

        try:
            self.go(reload=True)
        except:
            traceback.print_exc()
        
        self.thread = Thread(target=self.run)
        self.thread.start()
        
    def has_jabber_clients(self, jid=None):
        if not jid: return bool(self.clients)
        else: return self.clients.has_key(jid)
    
    def send_last20(self, jid):
        for prs in self.chat_users.values():
            prs['to'] = jid
            send(prs)
        for msg in self.last20:
            msg['to'] = jid
            send(msg)
        if self.topic:
            msg = Node("message", {"type": "groupchat", "from": self.name+u"@"+host, "to": jid})
            msg.addChild("subject").addData(self.topic)
            send(msg)
    
    def set_prs_status(self, jid, prs):
        nick = self.clients.get(jid)
        if not nick: return
        
        show = prs.getTag("show")
        if show: show = show.getData()
        if not show: show = u"online"
        
        status = prs.getTag("status")
        if status: status = status.getData()
        else: status = u""
        
        if status:
            self.chat.changestatus(nick.encode("utf-8"),  status.encode("utf-8"))
            return
        
        if show in (u"away", u"xa"):
            show = "AWAY"
        elif show in (u"dnd", ):
            show = "DND"
        else:
            show = "ONLINE"
        
        self.chat.changestatus(nick.encode("utf-8"), show)
    
    def join(self, jid, nick, prs, password=None):
        if self.clients.get(jid) == nick:
            self.set_prs_status(jid, prs)
            return
        if self.clients.get(jid): # or (nick != u"anonymous" and not password):
            send(gen_error(prs, "409", "cancel", "conflict"))
            return
            
        if self.chat_users.get(nick) and self.clients.get(jid) != nick:
            send(gen_error(prs, "409", "cancel", "conflict"))
            return
        
        if nick == u"anonymous":
            self.clients[jid] = nick
            self.send_last20(jid)
            prs = Node("presence", {"type":"available", "from": self.name+u"@"+host+u"/"+nick, "to": jid})
            x = prs.addChild("x")
            x.setNamespace("http://jabber.org/protocol/muc#user")
            x.addChild("item", {"affiliation":"none", "role": "visitor"})
            send(prs)
            return
            
        cookie, result = self.chat.login(nick, password if password else "")
        if result['status'] == 'ok':
            self.clients[jid] = nick
            self.send_last20(jid)
            self.set_prs_status(jid, prs)
            return
        
        elif result['status'] == 'needpassword':
            send(gen_error(prs, "401", "auth", "not-authorized"))
            return
        
        captcha = self.chat.getcaptcha(cookie=cookie)
        chash = sha1(captcha).hexdigest()   
        cid = "sha1+" + chash + "@bob.xmpp.org"
        
        cid = str(random.randrange(1000000,10000000))
        self.captcha_cache[jid] = [nick, password, cid, cookie, prs]
        msg = Node("message", {"from": self.name+u"@"+host, "to": jid, "id": cid})
        msg.addChild("body").addData(u"Увы, капча")
        
        c = msg.addChild("captcha")
        c.setNamespace("urn:xmpp:captcha")
        x = c.addChild("x", {"type": "form"})
        x.setNamespace("jabber:x:data")
        x.addChild("field", {"type": "hidden", "var": "FORM_TYPE"}).addChild("value").addData("urn:xmpp:captcha")
        x.addChild("field", {"type": "hidden", "var": "from"}).addChild("value").addData(self.name+u"@"+host)
        x.addChild("field", {"type": "hidden", "var": "challenge"}).addChild("value").addData(cid)
        x.addChild("field", {"type": "hidden", "var": "sid"}).addChild("value")
        l = x.addChild("field", {"label": u"Введите увиденный текст", "var": "ocr"})
        l.addChild("required")
        m = l.addChild("media")
        m.setNamespace("urn:xmpp:media-element")
        m.addChild("uri", {"type":"image/png"}).addData(cid)
        
        d = msg.addChild("data", {"cid": cid, "type": "image/png", "mag-age": "0"})
        d.setNamespace("urn:xmpp:bob")
        d.addData(b64encode(captcha))
        
        send(msg)

    def parse_captcha_iq(self, jid, node):
        if node['type'] != 'set': return
        print "parse captcha"
        nick, password, cid, cookie, prs = self.captcha_cache.get(jid, [None, None, None, None, None])
        if not cid or not cookie or not prs: return
        self.captcha_cache.pop(jid)
        
        try:
            captcha = node.getTag("captcha", {"xmlns":"urn:xmpp:captcha"})
            #print unicode(captcha)
            captcha = captcha.getTag("x").getTag("field", {"var":"ocr"}).getTag("value").getData()
        except:
            captcha = ""
        
        print "c =", captcha
        
        cookie, result = self.chat.login(nick, password, captcha=captcha, cookie=cookie)
        if result['status'] != 'ok':
            send(gen_error(prs, "406", "modify", "not-acceptable"))
            send(gen_error(prs, "401", "auth", "not-authorized"))
            if not self.has_jabber_clients():
                kill_room(self.name)
            raise NodeProcessed
            
        #self.cookies[jid] = cookie
        self.clients[jid] = nick
        self.send_last20(jid)
        self.set_prs_status(jid, prs)
        
    def parse_message(self, jid, node):
        if node['type'] != 'groupchat': return
        nick = self.clients.get(jid)
        if not nick or nick == u'anonymous': return
        
        body = node.getTag("body")
        if not body or not body.getData(): return
        body = body.getData()
        self.msg_id_cache[nick] = node['id']
        
        if self.chat.send_msg(nick.encode("utf-8"), body.encode("utf-8")).get('status') == 'notlogged':
            self.leave(jid, None, status=307)

    def stop(self):
        self.stopped = True
        for jid in self.clients.keys():
            self.leave(jid)
        
    def leave(self, jid, prs=None, status=None):
        nick = self.clients.get(jid)
        if not nick: return
        self.clients.pop(jid)
        node=Node("presence", {"type": "unavailable", "to": jid, "from": self.name+u"@"+host+u"/"+nick})
        if status: node.addChild("x", namespace="http://jabber.org/protocol/muc#user").addChild("status", {"code": str(status)})
        send(node)
        if nick != u"anonymous":
            self.chat.leave(nick)

    def run(self):
        while 1:
            if self.stopped: break
            try:
                self.go()
            except:
                traceback.print_exc()
                time.sleep(1)
        print "STOP", self.name
    
    def go(self, reload=False):
        #print time.time() - self.clients_timeout
        if time.time() - self.clients_timeout >= 30:
            #print "timeout"
            for nick in self.clients.values():
                if nick == u'anonymous': continue
                #self.chat.changestatus(nick)
                try: self.chat.send_action(nick, "listen", reload="1") #reload=0 если с предыдущей строчкой
                except KeyboardInterrupt: continue
                except: pass
            self.clients_timeout = time.time()

        data = self.chat.listen(reload)
        if self.stopped: return
        for item in data.get("users", []):
            #print "user", item
            #print
            if item.get("nick") == u"anonymous":
                print "WARNING!!! ANONYMOUS IN CHATOVOD!!!"
                continue
            if item['event'] == 'LEAVE':
                if not self.chat_users.get(item['nick']): continue
                self.chat_users.pop(item['nick'])
                self.send_node(Node("presence", {"type": "unavailable", "from": self.name+u"@"+host+u"/"+item['nick']}))
            else:
                sprs = Node("presence", {"type": "available", "from": self.name+u"@"+host+u"/"+item['nick']})
                x = sprs.addChild("x")
                x.setNamespace("http://jabber.org/protocol/muc#user")
                aff = 'owner' if item.get('adm')=='1' else ('admin' if item.get('m')=='1' else 'none')
                role = 'moderator' if aff!='none' else 'participant'
                x.addChild("item", {"affiliation":aff, "role": role})
                if item['s'] == 'AWAY':
                    sprs.addChild("show").addData("away")
                elif item['s'] == 'DND':
                    sprs.addChild("show").addData("dnd")
                elif item['s'] == 'CUSTOM':
                    sprs.addChild("status").addData(item.get("ss", u""))
                self.chat_users[item['nick']] = sprs
                self.send_node(sprs)
        
        for item in data.get('messages', []):
            #print "msg", item
            #print
            if item.get('channel') != 'main': continue
            if item.get('type') in (u'login', u'logout') or (not item.get('from') and item.get('type')!='me'):
                continue
            
            if item.get('type') == 'me':
                item['from'], item['text'] = item['text'].split(" ",1)
                item['text'] = u"/me " + item['text']
            
            if item.get("from") == u"anonymous":
                print "WARNING!!! ANONYMOUS IN CHATOVOD!!!"
                continue
            
            if self.msg_id_cache.get(item['from']):
                mid = self.msg_id_cache.pop(item['from'])
            else:
                mid = str(random.randrange(10000,100000))
                
            
            msg = Node('message', {
                'type':'groupchat',
                'from': self.name+u"@"+host+u"/"+item['from'],
                'id': mid
            })
           
            body = None
            try:
                #if "<" in item['text'] :
                body = XML2Node("<body>"+item['text'].encode("utf-8")+"</body>")
            except:
                print "cannot parse text", self.name
                #body = Node('body')
                #body.addData(item['text'])
            if body:
                body.setNamespace("http://www.w3.org/1999/xhtml")
            
            if body:
                text_body = u""
                for x in body.getPayload():
                    if not x: continue
                    if isinstance(x, unicode): text_body += x; continue
                    if x.getName() == 'br': text_body += u'\n'
                    elif x.getName() == 'img' and x['src']:
                        if 'chatovod.ru' in x['src'] and '/i/sm/' in x['src'] :
                            text_body += u' ' + x['alt'] + u' '
                            x['src'] = get_smile(x['src'])
                        else:
                            text_body += u' ' + x['src'] + u' ' + ((u'(' + x['alt'] + ') ') if x['alt'] else u'')
                        x['onload'] = u''
                    elif x.getName() == 'a' and x['onclick'] and '/media/?url=' in x['onclick']:
                        url = x['onclick'].split("/media/?url=",1)[-1].split("'",1)[0]
                        url = unquote(url)
                        text_body += url
                        x.setData(url)
                        x['src'] = url
                        
                    else: text_body += x.getCDATA()
                    
            else:
                text_body = item['text']
            #if item.get('type') == 'me' and text_body.find(item['from']+u" ") == 0:
            #    text_body = u"/me "+text_body[len(item['from'])+1:]
        
            msg.addChild('body').addData(text_body)
            if body:
                html = msg.addChild('html')
                html.setNamespace("http://jabber.org/protocol/xhtml-im")
                html.addChild(node=body)
            
            self.send_node(msg)
            
            tm = time.gmtime(int(item.get('t', 0))/1000)
            tm1 = time.strftime("%Y-%m-%dT%H:%M:%SZ", tm)
            tm2 = time.strftime("%Y%m%dT%H:%M:%S", tm)
            
            msg.addChild("delay", {"from": self.name+u"@"+host, "stamp": tm1}).setNamespace("urn:xmpp:delay")
            msg.addChild("x", {"stamp": tm2}).setNamespace("jabber:x:delay")
            
            self.last20.append(msg)
            if len(self.last20) > 20:
                self.last20 = self.last20[-20:]
        
        for item in data.get("events", []):
            #print "event", item
            #print
            if item.get('t') != 'news': continue
            
            body = item['text']
            try:
                if "<" in body:
                    body = XML2Node("<body>"+body.encode("utf-8")+"</body>")
                    body = body.getCDATA()
            except:
                print "cannot parse event text", self.name
            
            self.topic = body if body else None
            
            msg = Node("message", {"type": "groupchat", "from": self.name+u"@"+host})
            msg.addChild("subject").addData(self.topic if self.topic else "")
            self.send_node(msg)
    
    def send_node(self, node):
        for send_jid in self.clients.keys():
            node['to'] = send_jid
            send(node)

def create_room(name):
    room = Room(name)
    rooms[name] = room
    print "CREATE", name
    return room
    
def kill_room(name):
    room = rooms.get(name)
    if not room: return

    room.stop()
    rooms.pop(name)
    print "KILL", name

def get_rooms_list(please_dict=False):
    global rooms_list, rooms_list_time, rooms_list_dict
    if int(time.time()) - rooms_list_time < 30:
        return rooms_list_dict if please_dict else rooms_list
    
    rooms_list = []
    rooms_list_dict = {}
    rooms_list_time = int(time.time())
    
    for i in xrange(10):
        crooms = chatovod.get_rooms_list(i+1)
        if not crooms: break
        for croom in crooms:
            f=croom[0].rfind(".chatovod.ru/")
            if f <= 0: continue
            name = croom[0][:f] + "@" + host
            name = name[name.rfind("/")+1:]
            title = croom[1].encode("utf-8") + " (" + str(croom[2]) + ")"
            rooms_list.append( (name, title,) )
            rooms_list_dict[name] = (croom[1].encode("utf-8"), croom[2])
    
    return rooms_list_dict if please_dict else rooms_list

def socket_read():
    global sock
    return sock.recv(4096)

def read():
    global reader
    return reader.next()

def send(data):
    global sock, lock
    with lock:
        if not isinstance(data, str):
            data = unicode(data).encode("utf-8")
        return sock.sendall(data.translate(None, deletechars))

def connect():
    global config, sock, reader, host
    sock = socket.socket()
    server = config.get('server')
    if not server: server = config['host']
    sock.connect( (server, int(config['port']),) )
    reader = node_reader(socket_read)
    send(gen_stream_stream(config['host'], 'jabber:component:accept'))
    node = read()
    if node.getName() != "stream":
        print unicode(node)
        raise CExc("Invalid stanza")
    sid = node['id']
    shash = sha1(str(sid) + config['password']).hexdigest()
    handshake = Node("handshake")
    handshake.addData(shash)
    send(handshake)
    
    node = read()
    if node.getName() != 'handshake':
        if node.getName() == 'error':
            raise CExc(node.getChildren()[0].getName())
        print unicode(node)
        raise CExc("Invalid stanza")
    
    host = config['transport_host'].decode("utf-8")
    
def process():
    node = read()
    
    try:
        parse_node(node)
    except NodeProcessed: pass
    except KeyboardInterrupt: raise
    except:
        try:
            #print unicode(node)
            #print
            #print unicode(gen_error(node))
            send(gen_error(node))
        except:
            traceback.print_exc()
        raise

def parse_node(node):
    if node.getName() == "iq":
        if node['to'] == host: parse_my_iq(node)
        else: parse_iq(node)
        if node['type'] in ('get', 'set'):
            send(gen_error(node, "501" ,"cancel", "feature-not-implemented"))
    
    elif node.getName() == "presence":
        if node['to'] == host: pass
        else: parse_presence(node)
        
    elif node.getName() == "message":
        if node['to'] == host: pass
        else: parse_message(node)

def parse_message(node):
    if node['type'] == 'error': return
    jid, resource = jid_split(node['to'])
    #node['to'] = jid
    name = jid[:jid.find("@")].encode("utf-8")
    
    #TODO: fix xmlns=jabber:component:accept
    #send(gen_error(node, "403", "auth", "forbidden", text="Сообщения не поддерживаются", childs=True))
    
    if not resource:
        room = rooms.get(name)
        if room: room.parse_message(node['from'], node)

def parse_presence(node):
    if node['type'] == 'error': return
    jid, resource = jid_split(node['to'])
    #node['to'] = jid
    name = jid[:jid.find("@")].encode("utf-8")
    
    room = rooms.get(name)
    if room:
        #joined = rooms[name].clients.has_key(node['from'])
        joined = rooms[name].has_jabber_clients(node['from'])
    else:
        joined = False
    
    if not joined and not resource: return
    
    passwd = node.getTag("x", {"xmlns": "http://jabber.org/protocol/muc"})
    if passwd: passwd = passwd.getTag("password")
    if passwd: passwd = passwd.getData()
    
    if not room:
        if node['type'] == 'unavailable':
            return
        try: room = create_room(name)
        except chatovod.ChatovodError:
            send(gen_error(node, "404", "cancel", "remote-server-not-found"))
            return
    if node['type'] == 'unavailable':
        room.leave(node['from'], node)
        if not room.has_jabber_clients():
            kill_room(name)
    else:
        room.join(node['from'], resource, prs=node, password=passwd)

def parse_my_iq(node):
    query = node.getTag("query")
    if not query:
        return
    
    if query.getNamespace() == "http://jabber.org/protocol/disco#info":
        rquery = Node("query")
        rquery.setNamespace("http://jabber.org/protocol/disco#info")
        rquery.addChild("identity", {"category": "conference", "type": "text", "name": "Chatovod"})
        send(gen_iq_result(node, rquery))
        raise NodeProcessed
   
    elif query.getNamespace() == "http://jabber.org/protocol/disco#items":
        rquery = Node("query")
        rquery.setNamespace("http://jabber.org/protocol/disco#items")
        crooms = get_rooms_list()
        for croom in crooms:
            rquery.addChild("item", {"name": croom[1], "jid": croom[0]})
        send(gen_iq_result(node, rquery))
        raise NodeProcessed

def parse_iq(node):
    jid, resource = jid_split(node['to'])
    name = jid[:jid.find("@")].encode("utf-8")
    #print name, resource
    if not resource: # for chat
        if node.getTag("captcha"):
            #print "p c"
            room = rooms.get(name)
            #print "r", room
            if not room: return
            room.parse_captcha_iq(node['from'], node)
            return
    
        query = node.getTag("query")
        if not query:
            return
        
        if query.getNamespace() == "http://jabber.org/protocol/disco#info":
            rquery = Node("query")
            rquery.setNamespace("http://jabber.org/protocol/disco#info")
            croom = get_rooms_list(please_dict=1).get(name, ("", 0))
            rquery.addChild("identity", {"category": "conference", "type": "text", "name": croom[0]})
            rquery.addChild("feature", {"var": "http://jabber.org/protocol/muc"})
            rquery.addChild("feature", {"var": "muc_public"})
            rquery.addChild("feature", {"var": "muc_persistent"})
            rquery.addChild("feature", {"var": "muc_moderated"})
            rquery.addChild("feature", {"var": "muc_unsecured"})
            x = rquery.addChild("x", {"type": "result"})
            x.setNamespace("jabber:x:data")
            x.addChild("field", {"type": "hidden", "var": "FORM_TYPE"}).addChild("value").addData("http://jabber.org/protocol/muc#roominfo")
            x.addChild("field", {"label": "Описание комнаты", "var": "muc#roominfo_description"}).addChild("value")
            x.addChild("field", {"label": "Число присутствующих", "var": "muc#roominfo_occupants"}).addChild("value").addData(str(croom[1]))
            send(gen_iq_result(node, rquery))
            raise NodeProcessed
       
        elif query.getNamespace() == "http://jabber.org/protocol/disco#items":
            rquery = Node("query")
            rquery.setNamespace("http://jabber.org/protocol/disco#items")
            room = rooms.get(name)
            if room:
                for cuser in room.chat_users.keys():
                    rquery.addChild("item", {"name": cuser, "jid": name+'@'+host+"/"+cuser})
            send(gen_iq_result(node, rquery))
            raise NodeProcessed
        
def shutdown():
    global host, sock, reader
    for name in rooms.keys():
        kill_room(name)
    with lock:
        host = None
        sock = None
        reader = None

def main(run=0):
    if run == 0: load_config(config=config)
    connect()
    print "Connected"
    get_smile(u"http://st1.chatovod.ru/i/sm/icon_smile.gif")
    get_smile(u"http://st1.chatovod.ru/i/sm/icon_biggrin.gif")
    get_smile(u"http://st1.chatovod.ru/i/sm/lol1.gif")
    try:
        while 1:
            try:
                process()
            except StopIteration:
                print "Disconnected!"
                shutdown()
                time.sleep(1)
                return "reload"
            except KeyboardInterrupt: raise
            except CExc as exc: raise
            except:
                traceback.print_exc()
    finally:
        shutdown()

if __name__ == "__main__":
    try:
        run=0
        while main(run) == "reload":
            print "Restarting..."
            run+=1
    except KeyboardInterrupt:
        print
    except CExc as exc:
        print "Error:", str(exc)
