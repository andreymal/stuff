package net.modules;

import net.XmlReader;
import net.XmlWriter;

import java.util.Vector;
import java.io.IOException;

import net.ModuleListener;
import net.module;

public class clientinfo extends module{

ModuleListener ml;
XmlReader reader;
XmlWriter writer;
String itemjid, itemname, itemnode;
String feature, print;
private final String discoitems="http://jabber.org/protocol/disco#items";
private final String discoinfo="http://jabber.org/protocol/disco#info";
private final String xversion="jabber:iq:version";
private Vector commands;
private final String help0="disco [!account] [!jid] [type] [id]\nExample:\ndisco 0 jabber.org items disco_get";
private final String help1="getversion [!accnum] [!jid] [id]\nExample:\ngetversion 0 jabber.org getver";
private final String help2="sendversion [!accnum] [!to] [!id] [name] [version] [os]\nExample:\nsendversion 0 romeo@jabber.org result_id noname_Client 0.0.2_alpha J2ME";

public clientinfo(ModuleListener ml)
{
 this.ml=ml;
 commands=new Vector();
 commands.addElement("disco");
 commands.addElement("getversion");
 commands.addElement("sendversion");
}

public boolean parseYouIqXmlns(String xmlns){
 if(xmlns.equals(discoitems) || xmlns.equals(discoinfo) || xmlns.equals(xversion)) return true;
 else return false;
}
public void parseIq(int accnum, XmlReader reader, XmlWriter writer, String from, String type, String xmlns, String id) throws IOException, NullPointerException
{
 this.reader=reader; this.writer=writer;

///////////////////////////////

 if(type.equals("result")){
 if (this.reader.getAttribute("xmlns").equals(discoitems)) {
   while (this.reader.next() == XmlReader.START_TAG) {
    if (this.reader.getName().equals("item")) {
     itemjid = reader.getAttribute("jid");
     itemname = reader.getAttribute("name");
     itemnode = reader.getAttribute("node");
     if (itemjid!=null)
     {
      ml.sendModuleCommand("discoitem",accnum,from,itemjid,itemname,itemnode,id,null,null,null);
      print="disco "+from+": "+itemjid;
      ml.sendModulePrint(print);
     }
     this.reader.next();
    }  else {
     this.parseIgnore();
     }
   }
 } else if (this.reader.getAttribute("xmlns").equals(discoinfo)) {
   while (this.reader.next() == XmlReader.START_TAG) {
    if (this.reader.getName().equals("feature")) {
     feature = this.reader.getAttribute("var");
     if (feature!=null)
     {
      ml.sendModuleCommand("discofeature",accnum,from,feature,id,null,null,null,null,null);
      print="feature "+from+": "+feature;
      ml.sendModulePrint(print);
     }
     this.reader.next();
    }  else {
     this.parseIgnore();
     }
   } 


/////////////////////////////////////

 } else if (this.reader.getAttribute("xmlns").equals(xversion)) {
   itemname=null; itemnode=null; itemjid=null; //name, version, os соответственно :)
   while (this.reader.next() == XmlReader.START_TAG) {
    if (this.reader.getName().equals("name")) {
     itemname=this.parseText();
    }else if (this.reader.getName().equals("version")) {
     itemnode=this.parseText();
    }else if (this.reader.getName().equals("os")) {
     itemjid=this.parseText();
    }else this.parseIgnore();
   }

   ml.sendModuleCommand("versionresult",accnum,from,id,itemname,itemnode,itemjid,null,null,null);
   print="version "+from+":";
   if(itemname!=null) print=print+"\nName: "+itemname;
   if(itemnode!=null) print=print+"\nVersion: "+itemnode;
   if(itemjid!=null) print=print+"\nOS: "+itemjid;
   ml.sendModulePrint(print);

 }else this.parseIgnore();

///////////////////////////////

 }else if(type.equals("get")){

 if (this.reader.getAttribute("xmlns").equals(discoitems)) {
      while (this.reader.next() == XmlReader.START_TAG) {
       this.parseIgnore();
      }
      this.writer.startTag("iq");
      this.writer.attribute("type", "result");
      this.writer.attribute("id", id);
      this.writer.attribute("to", from);
      this.writer.startTag("query");
      this.writer.attribute("xmlns", "http://jabber.org/protocol/disco#items");

      this.writer.endTag(); // query
      this.writer.endTag(); // iq
      this.writer.flush();
 } else if (this.reader.getAttribute("xmlns").equals(discoinfo)) {
      while (this.reader.next() == XmlReader.START_TAG) {
       this.parseIgnore();
      }
      this.writer.startTag("iq");
      this.writer.attribute("type", "result");
      this.writer.attribute("id", id);
      this.writer.attribute("to", from);
      this.writer.startTag("query");
      this.writer.attribute("xmlns", "http://jabber.org/protocol/disco#info");

      this.writer.startTag("feature");
      this.writer.attribute("var", "jabber:iq:version");
      this.writer.endTag();

      this.writer.startTag("feature");
      this.writer.attribute("var", "http://jabber.org/protocol/disco#items");
      this.writer.endTag();

      this.writer.startTag("feature");
      this.writer.attribute("var", "http://jabber.org/protocol/muc");
      this.writer.endTag();

      this.writer.endTag(); // query
      this.writer.endTag(); // iq
      this.writer.flush();

/////////////////////////////////////

 } else if (this.reader.getAttribute("xmlns").equals(xversion)) {
      //System.out.println("getv");
      while (this.reader.next() == XmlReader.START_TAG) {
       this.parseIgnore();
      }
      ml.sendModuleCommand("versionrequest",accnum,from,id,null,null,null,null,null,null);
      print=from+" get your version (id "+id+")";
      ml.sendModulePrint(print);

 }else this.parseIgnore();

 }
}

 private void parseIgnore() throws IOException {
  int x;
  while ((x = this.reader.next()) != XmlReader.END_TAG) {
   if (x == XmlReader.START_TAG) {
    this.parseIgnore();
   }
  }
 }

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

public boolean parseYouThisCommand(String command){
 if(command.equals(commands.elementAt(0))
 || command.equals(commands.elementAt(1))
 || command.equals(commands.elementAt(2))
 ) return true;
 else return false;}

public void parseCommand(XmlWriter writer, String command, int accnum, String p1, String p2, String p3, String p4, String p5, String p6, String p7) throws IOException
{
 this.writer=writer;
 if(command.equals(commands.elementAt(0)))
 {
 if(p1!=null){
  if(p2==null){p2="items";};
  //if(!p2.equals("items") && !p2.equals("info")){p2="items";};
  if(p3==null)p3=p1;
  this.writer.startTag("iq");
  this.writer.attribute("type", "get");
  this.writer.attribute("to", p1);
  this.writer.attribute("id", p3);

  this.writer.startTag("query");
  if(p2.equals("info"))this.writer.attribute("xmlns", discoinfo);
  else this.writer.attribute("xmlns", discoitems);
  this.writer.endTag();

  this.writer.endTag();
  this.writer.flush();
 }else ml.sendModulePrint(help0);

////////////////////////////////

 }else if(command.equals(commands.elementAt(1))) {
 //System.out.println(p2);
 if(p1!=null){
  if(p2==null)p2=p1;
  this.writer.startTag("iq");
  //System.out.println("iq");
  this.writer.attribute("type", "get");
  this.writer.attribute("to", p1);
  //System.out.println("to");
  this.writer.attribute("id", p2);
  //System.out.println("id");

  this.writer.startTag("query");
  this.writer.attribute("xmlns", xversion);
  //System.out.println("xmlns");
  this.writer.endTag();

  this.writer.endTag();
  this.writer.flush();
 }else ml.sendModulePrint(help1);

////////////////////////////////

 }else if(command.equals(commands.elementAt(2))) {
 if(p1!=null && p2!=null){
      this.writer.startTag("iq");
      this.writer.attribute("type", "result");
      this.writer.attribute("id", p2);
      this.writer.attribute("to", p1);
      this.writer.startTag("query");
      this.writer.attribute("xmlns", xversion);

      if(p3!=null && !p3.equals("")){
       this.writer.startTag("name");
       this.writer.text(p3);
       this.writer.endTag();
      }if(p4!=null && !p4.equals("")){
       this.writer.startTag("version");
       writer.text(p4);
       this.writer.endTag();
      }if(p5!=null && !p5.equals("")){
       this.writer.startTag("os");
       this.writer.text(p5);
       this.writer.endTag();
      }

      this.writer.endTag(); // query
      this.writer.endTag(); // iq
      this.writer.flush();
 }else ml.sendModulePrint(help2);
 }
}

public Vector getYouCommands(){return commands;}
public String getHelp(String command)
{
 if(command.equals(commands.elementAt(0))) return help0;
 else if(command.equals(commands.elementAt(1))) return help1;
 else if(command.equals(commands.elementAt(2))) return help2;
 else return null;
}

}
