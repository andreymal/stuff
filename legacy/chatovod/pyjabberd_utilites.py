#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import sqlite3
from threading import RLock
try:
    from simplexml import NodeBuilder, Node, XML2Node
except:
    from xmpp.simplexml import NodeBuilder, Node, XML2Node

class Processed(Exception): pass

def gen_stream_stream(hostname, ns="jabber:client"):
		"""Генерирует stream:stream."""
		return "<?xml version='1.0'?><stream:stream xmlns='"+ns+\
		    "' xmlns:stream='http://etherx.jabber.org/streams' id='"+str(random.randrange(1000000000,10000000000))+\
		    "' from='"+hostname+"' version='1.0' xml:lang='ru'>"

def load_config(f='config.cfg', config=None):
	"""Читает файл как конфиг в формате ключ=значение в словарь config. Лишние пробелы удаляются, \
пустые и неполные строки игнорируются, строки с первым символом # игнорируются."""
	if config==None: config=globals()['config']
	try: fp=open(f,'r')
	except:
		sys.stdout.write("Предупреждение: файл конфигурации "+f+" не найден\n")
		return
	l=' '
	while len(l)>0:
		l=fp.readline()
		if not l or not '=' in l: continue
		if l[0]=='#': continue
		key,data=l.split('=',1)
		key=key.strip().lower()
		data=data.strip()
		if not key or not data: continue
		config[key]=data
	fp.close()
	
def escape(data):
	"""Экранирует строку data для базы данных (sqlite3)."""
	if not data: return "''"
	if isinstance(data, unicode): data=data.encode('utf-8')
	return "'"+data.replace('\x00','').replace("'","''")+"'" # кавычка экранируется двумя такими же
	
class DB:
	def __init__(self, database):
		self.db_conn=sqlite3.connect(database,check_same_thread=False)
		self.db=self.db_conn.cursor()
		self.rlock=RLock()
		
	def lock(self):
		self.rlock.acquire()
		
	def unlock(self):
		self.rlock.release()	
	
	def commit(self):
		self.db_conn.commit()
	
	def query(self, q):
		if isinstance(q, unicode): q=q.encode('utf-8')
		self.lock()
		try:
			self.db.execute(q)
			return self.db.fetchall()
		finally: self.unlock()
		
def node_reader(read, nb=None):
		"""Читает входящие данные и возвращает по одному объекту Node."""
		if not nb:
			nb=NodeBuilder()
			#nb.Parse('<stream:stream xmlns="jabber:client">')
		#print 'go'
		
		if nb.has_received_endtag(1) and nb.getDom().getChildren():
			for node in nb.getDom().getChildren(): yield node
		
		while 1:
			d=read()
			#print d
			#print 'read',d
			if not d:
				#print 'no data'
				return
			while '<?' in d:
				d1, nd = d.split('<?',1)
				nd, d2 = nd.split('>',1)
				d=d1+d2
				d=d.strip()
				del nd
			#print 'parse',d
			nb.Parse(d.replace('\x00',''))
			if not nb.has_received_endtag(1) or not nb.getDom().getChildren():
				if nb.has_received_endtag(0):
					#print nb.getDom()
					#print 'ret'
					return
				elif nb.getDom() and not nb.getDom().getChildren():
					yield Node(node=nb.getDom())
					#nb.getDom().namespace = None
					#if nb.getDom().attrs.get('xmlns'):
					#    nb.getDom().attrs.pop('xmlns')
					#nb.getDom().nsp_cache={}
				#else: print 'wtf?', unicode(nb.getDom()).encode('utf-8'), unicode(nb.getDom().getChildren()[0]).encode('utf-8')
				continue
			#print unicode(nb.getDom()).encode('utf-8')
			for node in nb.getDom().getChildren():
				#self.last_node=node
				node.parent = None
				yield node
			nb.getDom().setPayload([])
			
def jid_split(jid):
	"""Отделяет ресурс от JID."""
	if '/' in jid:
		return jid.split('/',1)
	else:
		return [jid,None]
		
def gen_error(node, error_code='500', error_type='wait', error_name='internal-server-error', text=None, childs=False):
	"""Генерирует ошибку из Node. По умолчанию internal-server-error."""
	err=Node(node.getName())
	if node['to']: err['from']=node['to']
	if node['from']: err['to']=node['from']
	if node['id']: err['id']=node['id']
	err['type']='error'
	if childs:
		for c in node.getChildren():
			if not c: continue
			err.addChild(node=c)
	e=err.addChild('error')
	e['type']=error_type
	e['code']=error_code
	e.addChild(error_name).setNamespace("urn:ietf:params:xml:ns:xmpp-stanzas")
	if text:
	    t = e.addChild("text")
	    t.setNamespace("urn:ietf:params:xml:ns:xmpp-stanzas")
	    t.addData(text)
	return err
	
def gen_iq_result(iq,query=None):
	"""Генерирует iq-result из iq-get/set.
	iq - iq-get/set Node, из которого генерировать result
	query - Node, который добавить в iq-result"""
	node=Node('iq')
	node['type']='result'
	if iq['from']: node['to']=iq['from']
	node['id']=iq['id']
	node['from']=iq['to']
	if query and isinstance(query,Node): node.addChild(node=query)
	return node
