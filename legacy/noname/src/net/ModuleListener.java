package net;

import javax.microedition.lcdui.*;

public interface ModuleListener {

 public void sendModuleCommand(String command, int accnum, String p1, String p2, String p3, String p4, String p5, String p6, String p7, String p8);
 public void sendCommand(String name, String p1, String p2, String p3, String p4, String p5, String p6, String p7, String p8);
 public void sendModulePrint(String print);

};
