package gui;
import javax.microedition.lcdui.*;
import java.util.Vector;
import java.util.Enumeration;

public class console extends Object implements CommandListener {

 Form form;
 String title;
 TextBox write;
 private Vector listeners = new Vector();

 private Command cwrite = new Command("Write", Command.OK, 0);
 private Command csend = new Command("Send", Command.OK, 1);

 public console(String title){
  this.title=title;
  form = new Form(title);
  form.addCommand(cwrite);
  form.setCommandListener(this);


  write = new TextBox("Command", "", 256, TextField.ANY);
  write.addCommand(csend);
  write.setCommandListener(this);
 }

//////////////////////////////////////////////

 public void commandAction(Command command, Displayable d)
 {
  if(command==cwrite){
   setDisplay(write);
  }
  else if(command==csend)
 {
  setDisplay(form);
  write(write.getString());
  String comm=write.getString();
  if(!comm.equals("")){
  if(comm.indexOf(' ')==-1)
  {
   String name=comm;
   sendCommand(name.toLowerCase(), null);
  }else{
   String name=comm.substring(0,comm.indexOf(' '));
   comm=comm.substring(comm.indexOf(' ')+1,comm.length());
   String[] params=new String[8];
    for(int i=0; i<8; i++)
    {
     if(comm.indexOf(' ')==-1){if(comm.length()>0){params[i]=comm; comm=""; continue;}else{params[i]=null; continue;}}
     if(i==7){params[i]=comm; break;}else{
      params[i]=comm.substring(0,comm.indexOf(' '));
      comm=comm.substring(comm.indexOf(' ')+1,comm.length());
     }
    }
   sendCommand(name.toLowerCase(), params[0],params[1],params[2],params[3],params[4],params[5],params[6],params[7]);
   if(name.toLowerCase().equals("clear")){this.clear(); setDisplay(form); System.gc();}
  }
  }
  write = new TextBox("Command", "", 256, TextField.ANY);
  write.addCommand(csend);
  write.setCommandListener(this);
 }
 }

public void restore()
{
 setDisplay(form);
}

//////////////////////////////////////////////

public void clear()
{
 for(int i=0; i<=form.size(); i++) form.delete(0);
}

public void write(String str)
{
 form.append(str+"\n");
 java.lang.System.out.println(str);
}

 public void sendCommand(String name, String param1, String param2, String param3, String param4, String param5, String param6, String param7, String param8)
 {
  for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
   GuiListener xl = (GuiListener) e.nextElement();
   xl.sendCommand(name,param1,param2,param3,param4,param5,param6,param7,param8);
  }
 }

 public void sendCommand(String name, String param1)
 {
  for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
   GuiListener xl = (GuiListener) e.nextElement();
   xl.sendCommand(name,param1);
  }
 }

 public void setDisplay(Displayable d)
 {
  for (Enumeration e = listeners.elements(); e.hasMoreElements();) {
   GuiListener xl = (GuiListener) e.nextElement();
   xl.setDisplay(d);
  }
 }

 public void addListener(final GuiListener xl) {
  if(!listeners.contains(xl)) listeners.addElement(xl);
 }

}//end console
