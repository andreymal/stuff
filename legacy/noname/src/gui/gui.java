package gui;

import javax.microedition.lcdui.Displayable;

public class gui extends Object {

 GuiListener listener;
 public static String name="";


 public static boolean isGui(){return false;}

 public gui(GuiListener listen)
 {

 }


//////////////////////////////////////////////

public void start()
{
 
}

public void minimize()
{

}

public void restore()
{
}

public void stop()
{
}


public void msg(String name, int accnum, String param1, String param2, String param3, String param4, String param5, String param6, String param7, String param8)
{

}

 public void sendCommand(String name, String param1, String param2, String param3, String param4, String param5, String param6, String param7, String param8)
 {
  listener.sendCommand(name,param1,param2,param3,param4,param5,param6,param7,param8);
 }

 public void sendCommand(String name, String param1)
 {
  listener.sendCommand(name,param1);
 }


 public void setDisplay(Displayable d)
 {
  listener.setDisplay(d);
 }

 public void msg(String name, int accnum, String param1)
 {
  this.msg(name,accnum,param1,null,null,null,null,null,null,null);
 }
}
