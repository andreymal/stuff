package net;

import net.XmlReader;
import net.XmlWriter;
import net.ModuleListener;
import java.io.IOException;
import java.util.Vector;

public abstract class module extends Object{

public boolean parseYouIqXmlns(String xmlns){return false;}
public void parseIq(int accnum, XmlReader reader, XmlWriter writer, String from, String type, String xmlns, String id) throws IOException{}
public boolean parseYouThisCommand(String command){return false;}
public void parseCommand(XmlWriter writer, String command, int accnum, String p1, String p2, String p3, String p4, String p5, String p6, String p7) throws IOException{} 
public Vector getYouCommands(){return null;}
public String getHelp(String command){return null;}
}
