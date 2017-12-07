#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from json import JSONDecoder
import urllib2
from threading import RLock

jd = JSONDecoder()
lock = RLock()

access_token = None

def api(method_name, args, method="POST", token=None, timeout=30):
    if not token and not token is False:
        token = access_token
    
    link = "https://api.vk.com/method/"+method_name
    if token: args['access_token'] = token
    
    params = ""
    
    for key in args.keys():
        data = args[key]
        if isinstance(data, unicode): data = data.encode("utf-8")
        elif isinstance(data, (list, tuple)): data = ",".join(map(lambda x:str(x), data))
        else: data = str(data)
        params += urllib2.quote(key) + "=" + urllib2.quote(data) + "&"
    params = params[:-1]
    
    if method == "GET":
        link += "?" + params
    
    req = urllib2.Request(link, method)
    
    if method == "POST":
        req.add_data(params)
    
    resp = urllib2.urlopen(req, timeout=timeout)
    data = resp.read()
        
    try:
        with lock: answer = jd.decode(data)
    except KeyboardInterrupt: raise
    except:
        answer = {"error":{
            "error_code":0,
            "error_msg":"Unparsed VK answer",
            "data": data
        }}
        
    return answer

if __name__ == "__main__":
    import code
    code.interact(local=globals())
