package gui;

import javax.microedition.lcdui.*;

public interface GuiListener {

 public void sendCommand(String name, String param1, String param2, String param3, String param4, String param5, String param6, String param7, String param8);
 public void sendCommand(String name, String param1);
 public void setDisplay(Displayable d);

};
