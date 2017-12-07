package net;

import javax.microedition.io.Connector;
import javax.microedition.io.StreamConnection;

import java.io.IOException;

import java.util.Vector;
import java.util.Enumeration;
//import java.lang.NullPointerException;

import net.module;
//import net.ModuleListener;

//import com.jcraft.jzlib.ZInputStream;
//import com.jcraft.jzlib.ZOutputStream;
//import com.jcraft.jzlib.JZlib;

/**
 * J2ME XMPP API Class
 * 
 * @author Swen Kummer, Dustin Hass, Sven Jost, Grzegorz Grasza
 * @version 4.0
 * @since 1.0
 */

public class Jxa extends Thread {

 final static boolean DEBUG = false;

 public final int accnum;
        
 private final String server, host, port, username, resource, password, myjid, caps, ver;
 private int priority;
 private String tmp, id, from, to, type, body, subject;
 private boolean register, auth;

 private XmlReader reader;
 private XmlWriter writer;

 private Vector listeners = new Vector();
 private Vector module    = new Vector();

 //public ModuleListener ml;

 /**
  * If you create this object all variables will be saved and the
  * method {@link #run()} is started to log in on jabber server and
  * listen to parse incomming xml stanzas. Use
  * {@link #addListener(XmppListener xl)} to listen to events of this object.
  * 
  * @param host the hostname/ip of the jabber server
  * @param port the port number of the jabber server
  * @param username the username of the jabber account
  * @param password the passwort of the jabber account
  * @param resource a unique identifier of the used resource, for e.g. "mobile"
  * @param priority the priority of the jabber session, defines on which
   * resource the messages arrive
  */

 public Jxa(Vector modules,final int accnum, final boolean register, final String username, final String host, final String password, final String server, final String port, final String resource, final String caps, final String ver) {
  this.module=modules;
  this.accnum=accnum;

  if(server!=null)
  {

   if(!port.equals("") && !port.equals("0"))
   {
    this.server = server+":"+port;
   }else
   {
    this.server = server+":5222";
   }
  }else if(port.equals("")==false & port.equals("0")==false)
  {
   this.server = host+":"+port;
  }else
   {this.server = host+":5222";} 
  this.register=register;
  this.host = host;
  this.port = port;
  this.username = username;
  this.password = password;
  this.resource = resource;
  this.caps = caps;
  this.ver = ver;
  this.myjid = username + "@" + host;
  auth=false;
  this.start();
 }

 public void run() {
  try {
   //System.out.println(username+" "+host+" "+password+" "+server+" "+port+" "+resource);
   //System.out.println("socket://" + this.server);
   final StreamConnection connection = (StreamConnection) Connector.open("socket://" + this.server, Connector.READ_WRITE);
   this.reader = new XmlReader(connection.openInputStream());
   this.writer = new XmlWriter(connection.openOutputStream());
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
		XmppListener xl = (XmppListener) e.nextElement();
		xl.onStep(1);
		}

  } catch (final Exception e) {
   System.out.println("run error"); this.connectionFailed();  
   return;
  }
  // connected
  try {
   this.login();
   this.parse();
  } catch(final NullPointerException npe)
  {System.out.println("JXA panic: NullPointerException"); npe.printStackTrace();
  } catch (final Exception e) {
                        try {
                            this.writer.close();
                            this.reader.close();
                        } catch (final IOException io) {
                            // io.printStackTrace();
                        }
                        // e.printStackTrace();
   // hier entsteht der connection failed bug (Network Down)
   System.out.println("i/o error"); this.connectionFailed();
  }
 }

 public void addListener(final XmppListener xl) {
  if(!listeners.contains(xl)) listeners.addElement(xl);
 }

 public void removeListener(final XmppListener xl) {
  listeners.removeElement(xl);
 }

 public boolean parseCommand(String name, String p1, String p2, String p3, String p4, String p5, String p6, String p7)
 {
     boolean known=false;
     try{
     for(int i=0; i<module.size(); i++)
     try{
      if( ((module)module.elementAt(i)).parseYouThisCommand(name)){
       try{((module)module.elementAt(i)).parseCommand(this.writer, name, accnum, p1, p2, p3, p4, p5, p6, p7);}
       catch(IOException ioe){this.connectionFailed();}
       known=true; break;
      }
      }catch(final NullPointerException npe)
      {
       if( module.elementAt(i)==null ){this.panic("module "+Integer.toString(i)+" is null!"); continue;}
      }
      }catch(final NullPointerException npe){if(module==null) this.panic("modules is null!");}
     return known;
 }

 public void login() throws IOException {
  // start stream
  this.writer.startTag("stream:stream");
  this.writer.attribute("to", this.host);
  this.writer.attribute("xmlns", "jabber:client");
  if(!register)this.writer.attribute("version", "1.0");
  this.writer.attribute("xmlns:stream", "http://etherx.jabber.org/streams");
  //this.writer.attribute("xmlns:xml", "http://www.w3.org/XML/1998/namespace");
  this.writer.flush();

  
  // log in
  if(register){
   this.writer.startTag("iq");
   this.writer.attribute("type", "set");
   this.writer.attribute("id", "auth");
   this.writer.startTag("query");
   //if(register){this.writer.attribute("xmlns", "jabber:iq:register");}else{this.writer.attribute("xmlns", "jabber:iq:auth");}
   this.writer.attribute("xmlns", "jabber:iq:register");
 
   this.writer.startTag("username");
   this.writer.text(this.username);
   this.writer.endTag();
   this.writer.startTag("password");
   this.writer.text(this.password);
   this.writer.endTag();
   //if(!register){
   // this.writer.startTag("resource");
   // this.writer.text(this.resource);
   // this.writer.endTag();
   //}
 
   this.writer.endTag(); // query
   this.writer.endTag(); // iq
   this.writer.flush(); 
  }
 
 }

 private void parse() throws IOException, NullPointerException {

  if (DEBUG) java.lang.System.out.println("*debug* parsing");
  this.reader.next(); // start tag
  while (this.reader.next() == XmlReader.START_TAG) {
   tmp = this.reader.getName();
   //System.out.println("<"+tmp+"/>");
   if (tmp.equals("message")) {
    this.parseMessage();
   } else if (tmp.equals("presence")) {
    this.parsePresence();
   } else if (tmp.equals("iq")) {
    this.parseIq();

   } else if (tmp.equals("stream:stream")) {
    continue;
   } else if (tmp.equals("stream:features")) {
    if(!auth)this.streamFeatures();else this.streamFeatures2();
   } else if (tmp.equals("challenge")) {
    if(!auth)this.parseChallenge();else this.parseChallenge2();
   } else if (tmp.equals("failure")) {
    this.parseFailure();
   } else if (tmp.equals("success")) {
    this.parseSuccess();
   } else {
    this.parseIgnore();
   }
  }
  this.reader.close();
 }

 private void streamFeatures() throws IOException
 {
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
		XmppListener xl = (XmppListener) e.nextElement();
		xl.onStep(2);
		}
  boolean digest=false;
  while (this.reader.next() == XmlReader.START_TAG) {
   if(this.reader.getName().equals("mechanisms")
   && this.reader.getAttribute("xmlns").equals("urn:ietf:params:xml:ns:xmpp-sasl")){
    while (this.reader.next() == XmlReader.START_TAG) {
     if(this.reader.getName().equals("mechanism")){
      tmp=this.parseText();
      if(tmp.equals("DIGEST-MD5"))digest=true;
      //System.out.println(tmp);
     }else this.parseIgnore();
    }

   }else{this.parseIgnore();}
  }
  //if(digest)System.out.println("md5"); else System.out.println("no md5");
  if(digest){
   this.writer.startTag("auth");
   this.writer.attribute("xmlns", "urn:ietf:params:xml:ns:xmpp-sasl");
   this.writer.attribute("mechanism", "DIGEST-MD5");
   this.writer.text("");

   this.writer.endTag(); // auth
   this.writer.flush(); 
  }else{
   this.writer.startTag("iq");
   this.writer.attribute("type", "set");
   this.writer.attribute("id", "auth");
   this.writer.startTag("query");
   this.writer.attribute("xmlns", "jabber:iq:auth");
 
   this.writer.startTag("username");
   this.writer.text(this.username);
   this.writer.endTag();
   this.writer.startTag("password");
   this.writer.text(this.password);
   this.writer.endTag();
   this.writer.startTag("resource");
   this.writer.text(this.resource);
   this.writer.endTag();
 
   this.writer.endTag(); // query
   this.writer.endTag(); // iq
   this.writer.flush(); 
  }
 }

 private String getNonce(String s)
 {
  String ret="";
  int start=0;
  for(int i=0; i<s.length()-7; i++)
   if(start==0){
    if(s.substring(i,i+6).equals("nonce="))
     if(s.substring(i+6,i+7).equals("\"")){start=i+7; i+=7;} else{ start=i+6;i+=6;}
   }else{
    if(s.substring(i,i+1).equals("\"") || s.substring(i,i+1).equals(",")){
     ret=s.substring(start,i); break;}
   }
  return ret;
 }

 public void parseChallenge() throws IOException
 {
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
		XmppListener xl = (XmppListener) e.nextElement();
		xl.onStep(3);
		}
  String ch=this.parseText();
  
  //System.out.println(new String(Util.base64decode(ch)));
  String nonce=getNonce(new String(Util.base64decode(ch)));
  String responce=Util.responseMd5Digest(username, password,
            host, "xmpp/"+host, nonce, "123456789abcd");
  //System.out.println(responce);

  this.writer.startTag("response");
  this.writer.attribute("xmlns","urn:ietf:params:xml:ns:xmpp-sasl");
  this.writer.text(responce);
  this.writer.endTag();
  this.writer.flush();
  this.auth=true;
 }

 public void parseFailure() throws IOException
 {
  this.parseIgnore();
  this.reader.close(); this.writer.close();
  this.connectionFailed();
 }

 public void parseChallenge2() throws IOException
 {
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
		XmppListener xl = (XmppListener) e.nextElement();
		xl.onStep(4);
		}
  this.parseText();
  //System.out.println(new String(Util.base64decode(ch)));
  //while (this.reader.next() == XmlReader.START_TAG) this.parseIgnore();

  this.writer.startTag("response");
  this.writer.attribute("xmlns","urn:ietf:params:xml:ns:xmpp-sasl");
  this.writer.endTag();
  this.writer.flush();
 }

 public void parseSuccess() throws IOException
 {
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
		XmppListener xl = (XmppListener) e.nextElement();
		xl.onStep(5);
		}
  //while (this.reader.next() != XmlReader.END_DOCUMENT) this.parseIgnore();
  this.parseText();
  

  this.writer.startTag("stream:stream");
  this.writer.attribute("to", this.host);
  this.writer.attribute("xmlns", "jabber:client");
  if(!register)this.writer.attribute("version", "1.0");
  this.writer.attribute("xmlns:stream", "http://etherx.jabber.org/streams");
  //this.writer.attribute("xmlns:xml", "http://www.w3.org/XML/1998/namespace");
  this.writer.flush();
 }

 private void streamFeatures2() throws IOException
 {
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
		XmppListener xl = (XmppListener) e.nextElement();
		xl.onStep(6);
		}
  boolean bind=false; boolean session=false;
  while (this.reader.next() == XmlReader.START_TAG) {
   if(this.reader.getName().equals("bind")
   && this.reader.getAttribute("xmlns").equals("urn:ietf:params:xml:ns:xmpp-bind"))
   {
    this.reader.next();
    this.writer.startTag("iq");
    this.writer.attribute("type","set");
    this.writer.attribute("id","bind_1");
    this.writer.startTag("bind");
    this.writer.attribute("xmlns","urn:ietf:params:xml:ns:xmpp-bind");
    this.writer.startTag("resource");
    this.writer.text(resource);
    this.writer.endTag(); //resource
    this.writer.endTag(); //bind
    this.writer.endTag(); //iq
    this.writer.flush();
   }
   else if(this.reader.getName().equals("session")
   && this.reader.getAttribute("xmlns").equals("urn:ietf:params:xml:ns:xmpp-session"))
   {
    this.reader.next();
    this.writer.startTag("iq");
    this.writer.attribute("type","set");
    this.writer.attribute("id","bind_1");
    this.writer.startTag("session");
    this.writer.attribute("xmlns","urn:ietf:params:xml:ns:xmpp-session");
    this.writer.endTag(); //session
    this.writer.endTag(); //iq
    this.writer.flush();
   }else this.parseIgnore();
  }
  //System.out.println("connect ok");
  for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
   XmppListener xl = (XmppListener) e.nextElement();
   if(register){xl.onRegister();}else{xl.onAuth(accnum);}
  }
  
 }

 /**
  * Closes the stream-tag and the {@link XmlWriter}.
  */
 public void logoff() {
  try {
   this.writer.endTag();
   this.writer.flush(); this.outXml(true, this.writer.getXml()); 
   this.writer.close();
  } catch (final Exception e) {
    System.out.println("logoff error");this.connectionFailed();
  }
 }

 /**
  * Sends a message text to a known jid.
  * 
  * @param to the JID of the recipient
  * @param msg the message itself
  */
 public void sendMessage(final String to, final String resource, final String type, final String subject, final String msg) {
  try {
   this.writer.startTag("message");
   if(type!=null){this.writer.attribute("type", type);}else{this.writer.attribute("type", "chat");}
   if(resource!=null){this.writer.attribute("to", to+"/"+resource);}else{this.writer.attribute("to", to);}
   if(subject!=null){this.writer.startTag("subject"); this.writer.text(subject); this.writer.endTag();}
   this.writer.startTag("body");
   this.writer.text(msg);
   this.writer.endTag();
   this.writer.endTag();
   this.writer.flush(); //this.outXml(true, this.writer.getXml()); 
  } catch (final Exception e) {
   // e.printStackTrace();
   System.out.println("sendmsg error"); this.connectionFailed();  
  }
 }

 /**
  * Sends a presence stanza to a jid. This method can do various task but
  * it's private, please use setStatus to set your status or explicit
         * subscription methods subscribe, unsubscribe, subscribed and
  * unsubscribed to change subscriptions.
  */
 public void sendPresence(final String to, final String type, final String show, final String status, final String priority, final String caps, final String ver) {
  try {
   this.writer.startTag("presence");
   if (type != null) {
    this.writer.attribute("type", type);
   }
   if (to != null) {
    this.writer.attribute("to", to);
   }
   this.writer.attribute("from", myjid+"/"+resource);
   if (show != null) {
    this.writer.startTag("show");
    this.writer.text(show);
    this.writer.endTag();
   }
   if (status != null) {
    this.writer.startTag("status");
    this.writer.text(status);
    this.writer.endTag();
   }

    try{
     Integer.parseInt(priority);
     this.writer.startTag("priority");
     this.writer.text(priority);
     this.writer.endTag();
     this.priority=Integer.parseInt(priority);
    }catch(Exception e){}

   if(caps != null) {
    this.writer.startTag("c");
    this.writer.attribute("xmlns", "http://jabber.org/protocol/caps");
    this.writer.attribute("node", caps);
    if(ver!=null){this.writer.attribute("ver", ver);}
    this.writer.endTag();
   }
   this.writer.endTag(); // presence
   this.writer.flush(); this.outXml(true, this.writer.getXml()); 

  } catch (final NullPointerException npe) 
   {try {this.writer.flush();}catch(final Exception e1)
   {}this.panic("sendPresence error");

  } catch (final Exception e) {
   // e.printStackTrace();
  System.out.println("presence error"); this.connectionFailed();  
  }
 }

 /*public void getDisco(final String jid, final String type, final String id)
 {
  if(jid!=null && id!=null){
  try {

   this.writer.startTag("iq");
   this.writer.attribute("type", "get");
   this.writer.attribute("to", jid);
   this.writer.attribute("id", id);

   this.writer.startTag("query");
   this.writer.attribute("xmlns", "http://jabber.org/protocol/disco#"+type);
   this.writer.endTag();

   this.writer.endTag();
   this.writer.flush();

  } catch (final Exception e) {
   this.connectionFailed(); 
  }
 }
 }*/

 public void removeAcc()
 {
  try {

   this.writer.startTag("iq");
   this.writer.attribute("type", "set");
   this.writer.attribute("id", "unreg");

   this.writer.startTag("query");
   this.writer.attribute("xmlns", "jabber:iq:register");
   this.writer.startTag("remove");
   this.writer.endTag();
   this.writer.endTag();

   this.writer.endTag();
   this.writer.flush();

  } catch (final NullPointerException npe) 
   {try {this.writer.flush();}catch(final Exception e1)
   {}this.panic("removeAcc error");


  } catch (final Exception e) {
   this.connectionFailed(); 
  }
 }

 public void setStatus(String show, String status, final String priority, final String caps, final String ver) {
  if(show!=null)if (show.equals("")) {
   show = null;
  }
  if(status!=null)if (status.equals("")) {
   status = null;
  }
  if(show!=null){
  if (show.equals("invisible")) {
   this.sendPresence(null, "invisible", null, null, priority, caps, ver);
  } else {
   this.sendPresence(null, null, show, status, priority, caps, ver);
  }
  }else{this.sendPresence(null, null, show, status, priority, caps, ver);}
 }

 /* public void subscribe(final String to) {
  this.sendPresence(to, "subscribe", null, null, 0, caps, ver);
 }

 public void unsubscribe(final String to) {
  this.sendPresence(to, "unsubscribe", null, null, 0, caps, ver);
 }

 public void subscribed(final String to) {
  this.sendPresence(to, "subscribed", null, null, 0, caps, ver);
 }

 public void unsubscribed(final String to) {
  this.sendPresence(to, "unsubscribed", null, null, 0, caps, ver);
 } */

 public void saveContact(final String jid, final String name, final Enumeration group, final String subscription) {
  try {
   this.writer.startTag("iq");
   this.writer.attribute("type", "set");
   this.writer.startTag("query");
   this.writer.attribute("xmlns", "jabber:iq:roster");
   this.writer.startTag("item");
   this.writer.attribute("jid", jid);
   if (name != null) {
    this.writer.attribute("name", name);
   }
   if (subscription != null) {
    this.writer.attribute("subscription", subscription);
   }
   if (group != null) {
    while (group.hasMoreElements()) {
     this.writer.startTag("group");
     this.writer.text((String) group.nextElement());
     this.writer.endTag(); // group
    }
   }
   this.writer.endTag(); // item
   this.writer.endTag(); // query
   this.writer.endTag(); // iq
   this.writer.flush(); this.outXml(true, this.writer.getXml()); 
  } catch (final Exception e) {
   // e.printStackTrace();
   System.out.println("savecontact error");this.connectionFailed(); 
  }
 }

 public void keepalive(final String jid) throws IOException{
  this.writer.startTag("iq");
  this.writer.attribute("to", jid);
  this.writer.attribute("type", "get");
  this.writer.attribute("id", "ping");
  this.writer.startTag("query");
  this.writer.attribute("xmlns", "jabber:iq:version");
  this.writer.endTag(); // query
  this.writer.endTag(); // iq
  this.writer.flush(); this.outXml(true, this.writer.getXml()); 
 }

 public void getRoster() throws IOException {
  this.writer.startTag("iq");
  this.writer.attribute("id", "roster");
  this.writer.attribute("type", "get");
  this.writer.startTag("query");
  this.writer.attribute("xmlns", "jabber:iq:roster");
  this.writer.endTag(); // query
  this.writer.endTag(); // iq
  this.writer.flush(); this.outXml(true, this.writer.getXml()); 
 }

 public void getBook() throws IOException, NullPointerException {
  this.writer.startTag("iq");
  this.writer.attribute("id", "roster");
  this.writer.attribute("type", "get");
  this.writer.startTag("query");
  this.writer.attribute("xmlns", "jabber:iq:private");
  this.writer.startTag("storage");
  this.writer.attribute("xmlns", "storage:bookmarks");
  this.writer.endTag(); // storage
  this.writer.endTag(); // query
  this.writer.endTag(); // iq
  this.writer.flush(); this.outXml(true, this.writer.getXml()); 
 }

/////////////////////////////////////////////////////////

 private void parseIq() throws IOException, NullPointerException {
  type = this.reader.getAttribute("type");
  id = this.reader.getAttribute("id");
  from = this.reader.getAttribute("from");

  //try{System.out.println("<iq type='"+type+"' from='"+from+"' id='"+id+"'/>");
  //}catch(Exception e){System.out.println("<iq 4to-to null/>");}

  if (type.equals("error")) {
   while (this.reader.next() == XmlReader.START_TAG) {
    // String name = reader.getName();
    if (this.reader.getName().equals("error")) {
     final String type1 = this.reader.getAttribute("type");
     final String code = this.reader.getAttribute("code");
     for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
      XmppListener xl = (XmppListener) e.nextElement();
      if(type1.equals("auth")){if(register){xl.onRegisterFailed(code);}else{xl.onAuthFailed(accnum, code);}  }else{xl.onIqFailed(accnum, type1,id,code);}
     }
    } else {
     this.parseText();
    }
   }
  } else if (type.equals("result") && (id != null) && id.equals("auth")) {
   // authorized
   this.reader.next();
   for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
    XmppListener xl = (XmppListener) e.nextElement();
    if(register){xl.onRegister();}else{xl.onAuth(accnum);}
   }

  } else if (type.equals("result") && (id != null) && id.equals("unreg")) {
   this.reader.next();
   for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
    XmppListener xl = (XmppListener) e.nextElement();
    xl.onRemoved(accnum);
   }

  } else if (type.equals("error") && (id != null) && id.equals("unreg")) {
   this.reader.next();
   for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
    XmppListener xl = (XmppListener) e.nextElement();
    xl.onRemoveFailed(accnum);
   }

  } else if(type.equals("result")) {
   while (this.reader.next() == XmlReader.START_TAG) {
    if (this.reader.getName().equals("query")) {
     if (this.reader.getAttribute("xmlns").equals("jabber:iq:roster")) {
      this.parseRoster();

     //} else if (this.reader.getAttribute("xmlns").equals("jabber:iq:version")) {
     // this.parseIgnore();
     } else if (this.reader.getAttribute("xmlns").equals("jabber:iq:private")) {
      this.parsePrivate();

    } else {
     boolean ig=true;
     for(int i=0; i<module.size(); i++){
      //System.out.println(i);
      if( ((module)module.elementAt(i)).parseYouIqXmlns(this.reader.getAttribute("xmlns"))){
       ((module)module.elementAt(i)).parseIq(accnum,this.reader,this.writer,from,type,this.reader.getAttribute("xmlns"),id);
       ig=false; break;
      }
     }
     if(ig) this.parseIgnore();
    }
    } else {
     this.parseIgnore();
    }
   }
  }else if(type.equals("get"))
  {
  while (this.reader.next() == XmlReader.START_TAG) {
     //if (this.reader.getAttribute("xmlns").equals("jabber:iq:version")) {

    //} else {
     boolean ig=true;
     for(int i=0; i<module.size(); i++){
      //System.out.println(i);
      if( ((module)module.elementAt(i)).parseYouIqXmlns(this.reader.getAttribute("xmlns"))){
       ((module)module.elementAt(i)).parseIq(accnum,this.reader,this.writer,from,type,this.reader.getAttribute("xmlns"),id);
       ig=false; break;
      }
     }
     if(ig) this.parseIgnore();
    //}

  }
  }else{while (this.reader.next() == XmlReader.START_TAG) {this.parseIgnore();}}
 }

///////////////////////////////

 private void parseRoster() throws IOException, NullPointerException {
      while (this.reader.next() == XmlReader.START_TAG) {
       if (this.reader.getName().equals("item")) {
        type = this.reader.getAttribute("type");
        String jid = reader.getAttribute("jid"),
        name = reader.getAttribute("name"),
        subscription = reader.getAttribute("subscription"),
        newjid = (jid.indexOf('/') == -1) ? jid : jid.substring(0, jid.indexOf('/'));
        boolean check = true;
        //for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
        // XmppListener xl = (XmppListener) e.nextElement();
        // xl.onContactRemoveEvent(accnum,newjid);
        //}
        while (this.reader.next() == XmlReader.START_TAG) {
         if (this.reader.getName().equals("group")) {
          for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
           XmppListener xl = (XmppListener) e.nextElement();
           xl.onContactEvent(accnum,newjid, name, this.parseText(), subscription);
          }
          check = false;
         } else if (this.reader.getName().equals("item")) {System.out.println("khm!");}else {
          this.parseIgnore();
         }
        }
        if (check && !subscription.equals("remove")) {
         for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
          XmppListener xl = (XmppListener) e.nextElement();
          xl.onContactEvent(accnum,jid, name, "", subscription);
         }
        }
       } else {
        this.parseIgnore();
       }
      }
 }


private void parsePrivate() throws IOException, NullPointerException {
      while (this.reader.next() == XmlReader.START_TAG) {
       if (this.reader.getName().equals("storage") && this.reader.getAttribute("xmlns").equals("storage:bookmarks")) {

      while (this.reader.next() == XmlReader.START_TAG) {
       if (this.reader.getName().equals("conference")) {
        String autojoin = reader.getAttribute("autojoin");
        String name = reader.getAttribute("name");
        String jid = reader.getAttribute("jid");
        while (this.reader.next() == XmlReader.START_TAG) {
         if (this.reader.getName().equals("nick")) {
          String nick=this.parseText();
          for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
           XmppListener xl = (XmppListener) e.nextElement();
           xl.onAddBook(accnum,autojoin, name, jid, nick);
          }
         }  else {
          this.parseIgnore();
          }
        }

       } else {
          this.parseIgnore();
          }
      }
       }  else {
        this.parseIgnore();
      }
     }
}


///////////////////////////////

 /**
  * This method parses all presence stanzas, including subscription requests.
  * 
  * @throws java.io.IOException is thrown if {@link XmlReader} or {@link XmlWriter}
  * throw an IOException.
  */
 private void parsePresence() throws IOException, NullPointerException {
  from = this.reader.getAttribute("from"); type = this.reader.getAttribute("type");
  String status = "", show = null;
  // int priority=-1;
  while (this.reader.next() == XmlReader.START_TAG) {
   tmp = this.reader.getName();
   if (tmp.equals("status")) {
    status = this.parseText();
   } else if (tmp.equals("show")) {
    show = this.parseText();
    // else if(tmp.equals("priority"))
    // priority = Integer.parseInt(parseText());
   } else {
    this.parseIgnore();
   }
  }
  if(show==null){show="online";}

  if (DEBUG) java.lang.System.out.println("*debug* from=" + from);
  if (DEBUG) java.lang.System.out.println("*debug* type=" + type);
  if (DEBUG) java.lang.System.out.println("*debug* status=" + status);
  if (DEBUG) java.lang.System.out.println("*debug* show=" + show);

  if ((type != null) && type.equals("unavailable")) {
   final String jid = (from.indexOf('/') == -1) ? from : from.substring(0, from.indexOf('/'));
                        for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
                                XmppListener xl = (XmppListener) e.nextElement();
                                xl.onOfflineEvent(accnum,jid, show);
                        }
  } else if ((type != null) && (type.equals("unsubscribed") || type.equals("error"))) {
                        for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
                                XmppListener xl = (XmppListener) e.nextElement();
                                xl.onUnsubscribeEvent(accnum,from);
                        }
  } else if ((type != null) && type.equals("subscribe")) {
                        for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
                                XmppListener xl = (XmppListener) e.nextElement();
                                xl.onSubscribeEvent(accnum,from);
                        }
  } else {
   final String jid = (from.indexOf('/') == -1) ? from : from.substring(0, from.indexOf('/'));
                        for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
                                XmppListener xl = (XmppListener) e.nextElement();
                                xl.onStatusEvent(accnum,jid, show, status);
                        }
  }
 }

 /**
  * This method parses all incoming messages.
  * 
  * @throws java.io.IOException is thrown if {@link XmlReader} or {@link XmlWriter}
  * throw an IOException.
  */
 private void parseMessage() throws IOException, NullPointerException {
  from = this.reader.getAttribute("from"); type = this.reader.getAttribute("type");
  id = this.reader.getAttribute("id");
  body = null; subject = null;
  while (this.reader.next() == XmlReader.START_TAG) {
   tmp = this.reader.getName();
   if (tmp.equals("body")) {
    body = this.parseText();
   } else if (tmp.equals("subject")) {
    subject = this.parseText();
   } else if (tmp.equals("request") && this.reader.getAttribute("xmlns").equals("urn:xmpp:receipts")) {
    this.writer.startTag("message");
    this.writer.attribute("to", from);
    if(id!=null){this.writer.attribute("id", id);}
    this.writer.startTag("received");
    this.writer.attribute("xmlns", "urn:xmpp:receipts");
    this.writer.endTag(); // received
    this.writer.endTag(); // message
    this.writer.flush(); this.parseIgnore(); //this.outXml(true, this.writer.getXml());
   }  else {
    this.parseIgnore();
   }
  }
  // (from, subject, body);
  String res = new String("");
  if(from.indexOf('/') != -1){res=from.substring(from.indexOf('/')+1);}
  if(res==null){res="null";}
  for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
   XmppListener xl = (XmppListener) e.nextElement();
   xl.onMessageEvent(accnum,(from.indexOf('/') == -1) ? from : from.substring(0, from.indexOf('/')), res, type, subject, body);
  }
 }

 /**
  * This method parses all text inside of xml start and end tags.
  * 
  * @throws java.io.IOException is thrown if {@link XmlReader} or {@link XmlWriter}
  * throw an IOException.
  */
 private String parseText() throws IOException {
  final String endTagName = this.reader.getName();
  final StringBuffer str = new StringBuffer("");
  int t = this.reader.next(); // omit start tag
  while (!endTagName.equals(this.reader.getName())) {
   if (t == XmlReader.TEXT) {
    str.append(this.reader.getText());
   }
   t = this.reader.next();
  }
  return str.toString();
 }

 /**
  * This method doesn't parse tags it only let the reader go through unknown
  * tags.
  * 
  * @throws java.io.IOException is thrown if {@link XmlReader} or {@link XmlWriter}
  * throw an IOException.
  */
 private void parseIgnore() throws IOException {
  int x;
  while ((x = this.reader.next()) != XmlReader.END_TAG) {
   if (x == XmlReader.START_TAG) {
    this.parseIgnore();
   }
  }
 }

 /**
  * This method is used to be called on a parser or a connection error.
         * It tries to close the XML-Reader and XML-Writer one last time.
         *
  */


 private void outXml(final boolean out, final String code)
{
 for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
  XmppListener xl = (XmppListener) e.nextElement();
  xl.onXml(accnum,out, code);
 }
}


 private void connectionFailed() {
                try {
                    this.writer.close();
                    this.reader.close();
                } catch (final Exception e) {
                    // io.printStackTrace();
                }
 System.out.println("vyzvali!");
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
                        XmppListener xl = (XmppListener) e.nextElement();
                        xl.onConnFailed(accnum);
                }
 }

private void panic(String p)
{
                for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
                        XmppListener xl = (XmppListener) e.nextElement();
                        xl.netPanic(p);
                }
}

};
