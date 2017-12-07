import net.Jxa;
import net.XmppListener;
import java.util.Vector;

public class account extends Object {

public Jxa net;

public String name,host,pass,server,port,res,caps,ver;

XmppListener xl;
int accnum;

public account(XmppListener xl, int accnum, String name, String host, String pass, String server, String port, String res,String caps,String ver)
{
 this.xl=xl;
 this.accnum=accnum;
 this.name=name;
 this.host=host;
 this.pass=pass;
 this.server=server;
 this.port=port;
 this.res=res;
 this.caps=caps;
 this.ver=ver;
}

public void connect(Vector m)
{
 net=new Jxa(m,accnum,false,name,host,pass,server,port,res,caps,ver);
 net.addListener(xl);
}

public void disconnect()
{
 if(net!=null)net.sendPresence(null,"unavailable",null,null,null,null,null);
 net=null;
 System.gc();
}

public boolean isConnected()
{
 if(net!=null)return true;
 return false;
}

}
