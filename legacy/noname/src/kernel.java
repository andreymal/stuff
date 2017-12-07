import javax.microedition.midlet.MIDlet;
import javax.microedition.lcdui.Display;
import javax.microedition.lcdui.Displayable;

import net.Jxa;
import net.XmppListener;

import net.module;
import net.ModuleListener;
import net.modules.*;

import gui.gui;
import gui.console;
import gui.GuiListener;

import java.util.Vector;

public class kernel extends MIDlet implements GuiListener, XmppListener, ModuleListener {

Display display = Display.getDisplay(this);

console console;
gui gui;
boolean isStart = false;
byte guist = 0;
Jxa reg;
Vector comm, helpcomm, acc, module;

public void pauseApp()
{

}

public void destroyApp(boolean u)
{
 for(int i=0; i<acc.size(); i++) ((account)acc.elementAt(i)).disconnect();
 notifyDestroyed();
}

public void startApp()
{
 if(!isStart)
 {
  isStart=true;
  console=new console("noname 0.0.2 alpha");
  console.addListener(this);
  console.write("Starting...");
  comm=new Vector();
  helpcomm=new Vector();
  acc=new Vector();
  module=new Vector(); this.startModules();

  comm.addElement("gui");
  comm.addElement("connect");
  comm.addElement("register");
  comm.addElement("presence");
  comm.addElement("disconnect");
  comm.addElement("status");
  comm.addElement("message");
  comm.addElement("getroster");
  comm.addElement("getbook");
  comm.addElement("removeacc");
  //comm.addElement("disco");
  comm.addElement("help");
  comm.addElement("print");
  comm.addElement("addacc");
  comm.addElement("delacc");

  helpcomm.addElement("Graphical user interface.\ngui [on/off/min]\nExample:\ngui on");
  helpcomm.addElement("connect [!accnum]\nExample:\nconnect 0");
  helpcomm.addElement("register [!name] [!host] [!pass] [server/ip] [port]\nExample:\nregister user jabber.com 123456 jabber.com 5222");
  helpcomm.addElement("presence [!accnum] [!to or 'none'] [!type or 'none'] [show or 'none'] [status or 'none'] [priority (int)]\nExample:\npresence 0 user@jabber.org available chat HI-ALL! 30");
  helpcomm.addElement("disconnect [!accnum]\nExample:\ndisconnect 0");
  helpcomm.addElement("status [!accnum] [show or 'none'] [status or 'none'] [priority (int) or 'none'] [caps or 'none'] [ver or 'none']]nExample:\nstatus 0 chat HI-ALL! 30 Jabber-client 0.0.0-megaalpha");
  helpcomm.addElement("message [!accnum] [!to] [!type or 'none'] [!request(1/0)] [!id] [!text] \nExample:\nmessage 0 user@jabber.org chat 0 msgid I'm in Jabber!");
  helpcomm.addElement("getroster [!accnum]\nExample:\ngetroster 0");
  helpcomm.addElement("Get bookmarks.\ngetbook [!accnum]\nExample:\ngetbook 0");
  helpcomm.addElement("Delete connected account.\nremoveacc [!accnum]Example:\nremoveacc 0");
  //helpcomm.addElement("disco [!accnum] [!to] [items/info] [id]\nExample:\ndisconnect");
  helpcomm.addElement(":)");
  helpcomm.addElement("Print text in console.\nExample:\nprint Hello, World!!!!");
  helpcomm.addElement("addacc [!name] [!host] [!pass] [server/ip] [port] [resource]\nExample:\naddacc user jabber.com 123456 jabber.com 5222 console");
  helpcomm.addElement("delacc [!number]\nExample:\ndelacc 0");

  sendCommand("gui","on");

  
  //sendCommand("addacc","andreymal","amj.ath.cx","fuckyou","127.0.0.1","5222","noname1",null,null);
  /*
  sendCommand("addacc","andreymal","amj.ath.cx","fuckyou","127.0.0.1","5222","noname2",null,null);
  sendCommand("addacc","andreymal","amj.ath.cx","fuckyou","127.0.0.1","5222","noname3",null,null);
  sendCommand("addacc","andreymal","amj.ath.cx","fuckyou","127.0.0.1","5222","noname4",null,null);
  */
  //sendCommand("connect","0");
  /*sendCommand("connect","1");
  sendCommand("connect","2");
  sendCommand("connect","3");
  */

  System.gc();

 }
}

private void startModules()
{
 try{
  Class.forName("net.modules.clientinfo");
  module.addElement(new clientinfo(this));
 }catch(Exception e){}
 //try{
 // Class.forName("net.modules.version");
 // module.addElement(new version(this));
 //}catch(Exception e){}
}

public int findCommand(String name)
{
if(name!=null)
 for(int i=0; i<comm.size(); i++)
 {
  String s= (String) comm.elementAt(i);
  if (s.equals(name)) return i;
 }
 return -1;
}



public void sendCommand(String name, String param1, String param2, String param3, String param4, String param5, String param6, String param7, String param8)
{
int accnum=-1;
if(param1!=null)try{accnum=Integer.parseInt(param1);}catch(Exception e){}

int num=findCommand(name);
if(num==0) //gui
{
  if(param1.toLowerCase().equals("on") & guist==0)
  {
   gui=new gui(this);
   if(gui.isGui())
   {
    guist=1; gui.start();
   }else
   {
    gui=null; guist=0; console.write("GUI is empty."); console.restore();
   }
  }else if(param1.toLowerCase().equals("on") & guist==2)
  {
   gui.restore(); guist=1;
  }else if(param1.toLowerCase().equals("off") & guist==0)
  {
   gui=null; console.restore(); guist=0;
  }else if(param1.toLowerCase().equals("off") & guist!=0)
  {
   gui.stop(); gui=null; console.restore(); guist=0;
  }else if(param1.toLowerCase().equals("min") & guist==1)
  {
   gui.minimize(); guist=2; console.restore();
  }

//--------

} else if (num==1) //connect
{
 if(accnum>-1 && accnum<acc.size())
 {
  ((account)acc.elementAt(accnum)).connect(module);
 }else console.write("Account not found");

//--------

} else if (num==2) //register
{
 if(param1!=null && param2!=null && param3!=null){
 if(param4==null){param4=param2;}
 if(param5==null){param5="5222";}
 if(param6==null){param6="noname";}
 reg=new Jxa(module,-1, true, param1, param2, param3, param4, param5, param6, "0","1");
 reg.addListener(this);
 } else {console.write("Command: register [name] [host] [pass]");}

//--------

} else if(num==3) //presence
{
if(param1!=null && param2!=null && param3!=null){
 

 if(param2!=null) if(param2.equals("none")){param2=null;}
 if(param3!=null) if(param3.equals("none")){param3=null;}
 if(param4!=null) if(param4.equals("none")){param4=null;}
 if(param5!=null) if(param5.equals("none")){param5=null;}

 String vers =(gui.name!=null) ? gui.name : "";
 if( ((account) acc.elementAt(accnum) ).isConnected() )
  {((account) acc.elementAt(accnum) ).net.sendPresence(param2, param3, param4, param5, param6, "noname","0.0.2 alpha "+vers);}
} else {console.write("Command: presence [account] [to] [type]");}

//--------

} else if(num==4) //disconnect
{
 if(param1!=null && accnum>-1 && accnum<acc.size())
  if( ((account) acc.elementAt(accnum) ).isConnected() ){ ((account) acc.elementAt(accnum)).disconnect(); }
 else if(accnum>=acc.size())console.write("Account not found");
 else {console.write("Command: disconnect [account]");}

//--------

} else if(num==5) //status
{
 if(param1!=null && accnum>-1 && accnum<acc.size())
 {
  if(param2!=null) if(param2.equals("none")){param2=null;}
  if(param3!=null) if(param3.equals("none")){param3=null;}
  if(param4!=null) if(param4.equals("none")){param4="5";}
  if(param4==null){param4="n";}
  if(param5!=null) if(param5.equals("none")){param5=null;}
  if(param6!=null) if(param6.equals("none")){param6=null;}
  if( ((account) acc.elementAt(accnum) ).isConnected() )
  {
   String vers =(gui.name!=null) ? gui.name : "";
   if(param4!=null && param5!=null){
    ((account) acc.elementAt(accnum) ).net.setStatus(param2, param3, param4, param5, param6);
   }else{
    ((account) acc.elementAt(accnum) ).net.setStatus(param2, param3, param4,  "noname Client","0.0.2 alpha "+vers);
   }
  }
 }
 else if(accnum>=acc.size())console.write("Account not found");
 else {console.write("Command: status [account]");}

//--------

} else if(num==6) //message
{
if(param1!=null && param2!=null && param3!=null && param4!=null && param5!=null && param6!=null && accnum>-1 && accnum<acc.size()){

 if(param3!=null) if(param3.equals("none")){param3="chat";}

 String msg="";
 if(param6!=null)msg=msg+" "+param6;
 if(param7!=null)msg=msg+" "+param7;
 if(param8!=null)msg=msg+" "+param8;
 if( ((account) acc.elementAt(accnum) ).isConnected() && msg!="") ((account) acc.elementAt(accnum) ).net.sendMessage(param2,null,param3,null,msg);
}
else if(accnum>=acc.size())console.write("Account not found");
else{console.write("Command: message [account] [to] [type or 'none'] [request (1/0)] [id] [body]");}

//--------

} else if (num==7) //getroster
{
 if(param1!=null && accnum>-1 && accnum<acc.size())
 {
  if( ((account) acc.elementAt(accnum) ).isConnected() ){

   try{ ((account) acc.elementAt(accnum) ).net.getRoster(); } catch(Exception e){ console.write("Roster Exception!"); }

  }else{console.write("Not connect!");}
 }else if(accnum>=acc.size()){console.write("Account not found");}
 else{console.write("Command: getroster [account]");}

//--------

} else if (num==8) //getbook
{
 if(param1!=null && accnum>-1 && accnum<acc.size())
 {
  if( ((account) acc.elementAt(accnum) ).isConnected() ){

   try{ ((account) acc.elementAt(accnum) ).net.getBook(); } catch(Exception e){ console.write("Book Exception!"); }

  }else{console.write("Not connect!");}
 }else if(accnum>=acc.size()){console.write("Account not found");}
 else{console.write("Command: getroster [account]");}

//--------

} else if (num==9) //removeacc
{
 if(param1!=null && accnum>-1 && accnum<acc.size())
 {
  if( ((account) acc.elementAt(accnum) ).isConnected() ){

   try{ ((account) acc.elementAt(accnum) ).net.removeAcc(); } catch(Exception e){ console.write("Delete Exception!"); }

  }else{console.write("Not connect!");}
 }else if(accnum>=acc.size()){console.write("Account not found");}
 else{console.write("Command: getroster [account]");}

//--------

/*} else if(num==10) //disco
{if(param1!=null && param2!=null && accnum>-1 && accnum<acc.size())
 {
  if(param3==null){param3="items";};
  if(!param3.equals("items") && !param3.equals("info")){param3="items";};
  if(param4==null){param4=param2;}
  if( ((account) acc.elementAt(accnum) ).isConnected() ){((account) acc.elementAt(accnum) ).net.getDisco(param2,param3,param4);}
 }else if(accnum>=acc.size()){console.write("Account not found");
 }else{console.write("Command: disco [account] [to]");}

//--------
*/
} else if(num==10) //help
{
 int num1=findCommand(param1);
 if(num1>-1 && num1<helpcomm.size()){console.write((String)helpcomm.elementAt(num1));
 }else{
  int finded=-1;
  int modulenum=-1;
  try{
  for(int i=0; i<module.size(); i++)
   if( ((module)module.elementAt(i)).getYouCommands()!=null )
    for(int k=0; k<((module)module.elementAt(i)).getYouCommands().size(); k++)
     if(((module)module.elementAt(i)).getYouCommands().elementAt(k).equals(param1)){finded=k; modulenum=i;}
 }catch(Exception e){}
 if(finded>-1 && modulenum>-1)
 {
  console.write( ((module)module.elementAt(modulenum)).getHelp(param1) );
 }else{

 String out="";

 try{
  for(int i=0; i<module.size(); i++)
   if( ((module)module.elementAt(i)).getYouCommands()!=null )
    for(int k=0; k<((module)module.elementAt(i)).getYouCommands().size(); k++)
     out=out+((module)module.elementAt(i)).getYouCommands().elementAt(k)+", ";
 }catch(Exception e){}

 for(int i=0; i<comm.size()-1; i++) out=out+(String) comm.elementAt(i)+", ";
 out=out+(String) comm.elementAt(comm.size()-1)
 +"\n[!name] - binding param\n[name or 'none'] - you can write 'none' to param";
 console.write(out);
 }
 }

} else if(num==11) //write
{
 String s="";
 if(param1!=null)s=s+param1;
 if(param2!=null)s=s+" "+param2;
 if(param3!=null)s=s+" "+param3;
 if(param4!=null)s=s+" "+param4;
 if(param5!=null)s=s+" "+param5;
 if(param6!=null)s=s+" "+param6;
 if(param7!=null)s=s+" "+param7;
 if(param8!=null)s=s+" "+param8;
 console.write(s);
} else if(num==12) //addacc
{
 if(param1!=null && param2!=null && param3!=null){
 if(param4==null){param4=param2;}
 if(param5==null){param5="5222";}
 if(param6==null){param6="noname";}
 String vers =(gui.name!=null) ? gui.name : "";
 account n=new account(this,acc.size(), param1,param2,param3,param4,param5,param6,"noname","0.0.2 alpha "+vers);
 acc.addElement(n);
 console.write("Number of "+param1+"@"+param2+" is "+Integer.toString(acc.size()-1));
 } else {console.write("Command: addacc [name] [host] [pass]");}

//--------

} else if(num==13) //delacc
{

 int k=-1;
 try{k=Integer.parseInt(param1);}catch(Exception e){}
 if(k>-1 && k<acc.size())
 {
  acc.removeElementAt(k); console.write("Account "+Integer.toString(k)+" removed.");
 }else if(acc.size()!=0) console.write("Command: delacc [0.."+Integer.toString(acc.size()-1)+"]"); else console.write("No accounts.");

//--------

} else if(name.equals("debug"))
{

 int tmp=guist;
 console.write("guiStatus="+Integer.toString(tmp));
 //if(isConnect){console.write("isConnect=true");}else{console.write("isConnect=false");}

} else if(name.equals("clear"))
{console.clear();
} else if(name.equals("exit") | name.equals("quit"))
{
 console.write("Bye!"); if(guist!=0){gui.stop();} destroyApp(true);
} else if(name.equals("testing"))
{ if(param1!=null){console.write("'"+param1+"'");}
  if(param2!=null){console.write("'"+param2+"'");}
  if(param3!=null){console.write("'"+param3+"'");}
  if(param4!=null){console.write("'"+param4+"'");}
  if(param5!=null){console.write("'"+param5+"'");}
  if(param6!=null){console.write("'"+param6+"'");}
  if(param7!=null){console.write("'"+param7+"'");}
  if(param8!=null){console.write("'"+param8+"'");}
}else
{
 if(accnum>-1){
  if( ((account)acc.elementAt(accnum)).net.parseCommand(name, param2, param3, param4, param5, param6, param7, param8))return;
 }

 console.write("Unknown command! Write 'help'.'");
}
}

public void setDisplay(Displayable d)
{
 display.setCurrent(d);
}

/////////////////////////////////////////////
public void sendCommand(String name, String param1)
{
 sendCommand(name,param1,null,null,null,null,null,null,null);
}


public void onConnFailed(final int accnum)
{
 if(guist!=1){console.write("Connect error!");}
 if(guist!=0){gui.msg("onConnFailed",accnum,null);}
}

public void onAuth(final int accnum)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+" connected!");}
 if(guist!=0){gui.msg("connected",accnum,null);}
}

public void onAuthFailed(final int accnum, final String message)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": auth error "+message);}
 if(guist!=0){gui.msg("onAuthFailed",accnum,message);}
}

public void onIqFailed(final int accnum, final String type, final String id, final String code)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": Iq error "+type+": "+code);}
 if(guist!=0){gui.msg("onIqFailed",accnum,type,id,code,null,null,null,null,null);}
}

public void onMessageEvent(final int accnum, final String from, final String resource, final String type, final String subject, final String body)
{
 if(guist!=1){if(type==null){console.write(Integer.toString(accnum)+": msg from "+from+"/"+resource+":\n"+body);}else{console.write(type+" message from "+from+"/"+resource+":\n"+body);}}
 if(guist!=0){gui.msg("message",accnum,from,resource,type,subject,body,null,null,null);}
}

public void onContactRemoveEvent(final int accnum, final String jid)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": removed "+jid);}
 if(guist!=0){gui.msg("onContactRemoveEvent",accnum,jid);}
}

public void onContactEvent(final int accnum, final String jid, final String name, final String group, final String subscription)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": contact "+jid+" is known as " +name);}
 if(guist!=0){gui.msg("onContactEvent",accnum,jid,name,group,subscription,null,null,null,null);}
}

public void onOfflineEvent(final int accnum, final String jid, final String status)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": "+jid+" is offline");}
 if(guist!=0){gui.msg("onOfflineEvent",accnum,jid,status,null,null,null,null,null,null);}
}

public void onStatusEvent(final int accnum, final String jid, final String show, final String status)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": "+jid+" is "+show);}
 if(guist!=0){gui.msg("onStatusEvent",accnum,jid,show,status,null,null,null,null,null);}
}

public void onSubscribeEvent(final int accnum, final String jid)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": "+jid+" subscribed");}
 if(guist!=0){gui.msg("subscribe",accnum,jid,null,null,null,null,null,null,null);}
}

public void onUnsubscribeEvent(final int accnum, final String jid)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": "+jid+" unsubscribed");}
 if(guist!=0){gui.msg("unsubscribe",accnum,jid,null,null,null,null,null,null,null);}
}

public void onAddBook(final int accnum, final String autojoin, final String name, final String jid, final String nick)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+": bookmark "+name+" - "+jid+"\nNick: "+nick);}
 if(guist!=0){gui.msg("onAddBook",accnum,autojoin,name,jid,nick,null,null,null,null);}
}
public void onXml(final int accnum, final boolean out, final String code)
{ 
}

/*public void onDiscoItem(final int accnum, final String from, final String itemjid, final String itemname, final String id)
{ 
 if(guist!=1){if(itemname!=null){console.write("disco "+from+": "+itemname+" - "+itemjid);}else{console.write("disco "+from+": "+itemjid);} }
 if(guist!=0){gui.msg("onDiscoItem",accnum,from,itemjid,itemname,id,null,null,null,null);}
}

public void onDiscoFeature(final int accnum, final String from, final String feature, final String id)
{ 
 if(guist!=1){console.write("feature "+from+": "+feature);}
 if(guist!=0){
  if(
	  feature.equals("jabber:iq:version") 			//поддерживаемые фичи
	||feature.equals("presence")  
	||feature.equals("iq")
	||feature.equals("http://jabber.org/protocol/disco#info")
  )
  gui.msg("onDiscoFeature",accnum,from,feature,id,"1",null,null,null,null);
  else gui.msg("onDiscoFeature",accnum,from,feature,id,"0",null,null,null,null);
 }
}*/

public void onRegister()
{
 if(guist!=1){console.write("Registered!");}
 if(guist!=0){gui.msg("onRegister",-1,null,null,null,null,null,null,null,null);}
 reg=null; System.gc();
}

public void onRegisterFailed(final String code)
{
 if(guist!=1){console.write("Reg error: "+code);}
 if(guist!=0){gui.msg("onRegisterFailed",-1,code,null,null,null,null,null,null,null);}
 reg=null; System.gc();
}

public void onRemoved(final int accnum)
{
 if(guist!=1){console.write("Account "+Integer.toString(accnum)+" removed :(");}
 if(guist!=0){gui.msg("onRemoved",accnum,null,null,null,null,null,null,null,null);}
 ((account) acc.elementAt(accnum) ).net=null; System.gc();
}
public void onRemoveFailed(final int accnum)
{
 if(guist!=1){console.write("Remove error!");}
 if(guist!=0){gui.msg("onRemoveFailed",accnum,null,null,null,null,null,null,null,null);}
}

public void onStep(int step)
{
 if(step==1) console.write("Start connection...");
 if(step==2) console.write("Select auth mechanism...");
 if(step==3) console.write("Send login and password...");
 if(step==4) console.write("Authed...");
 if(step==5) console.write("New stream...");
 if(step==6) console.write("Set resources...");
}

public void netPanic(String panic){console.write(panic);}

//public void onModuleParse(String command, String p1, String p2, String p3, String p4, String p5, String p6, String p7, String p8)
//{

//}
/////////////////////////////////////////////

public void sendModuleCommand(String command, int accnum, String p1, String p2, String p3, String p4, String p5, String p6, String p7, String p8)
{
 if(guist!=0)gui.msg(command,accnum,p1,p2,p3,p4,p5,p6,p7,p8);
}

public void sendModulePrint(String print)
{
 if(guist!=1)console.write(print);
}



/////////////////////////////////////////////


}//end kernel
