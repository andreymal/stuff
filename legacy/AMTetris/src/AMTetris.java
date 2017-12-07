/*
 * To change this template, choose Tools | Templates
 * and open the template in the editor.
 */

import javax.microedition.lcdui.Display;
import javax.microedition.lcdui.Displayable;
import javax.microedition.midlet.MIDlet;

/**
 * @author andreymal
 */
public class AMTetris extends MIDlet {
    private Display d;
    private TetrisCanv tetris;
    boolean started=false;
    private TetrisMenu menu;
    Displayable curr;

    public void startApp() {
      if(!started){
        d=Display.getDisplay(this);
        //tetris=new TetrisCanv(10,20);
        //d.setCurrent(tetris);
        menu=new TetrisMenu(this);
        d.setCurrent(menu);
        curr=menu;
        started=true;
      }else{
          d.setCurrent(curr);
      }
    }
    
    public void pauseApp() {
        tetris.pause();
    }
    
    public void destroyApp(boolean unconditional) {
        notifyDestroyed();
    }
    
    public void startGame(int x, int y, int lvl, int lines, int on3d){
        if(on3d!=0)on3d=100-on3d;
        tetris=new TetrisCanv(this,on3d,x,y,lvl, lines);
        d.setCurrent(tetris);
        curr=tetris;
        System.gc();
    }
    
    public void stopGame(){
        d.setCurrent(menu);
        curr=menu;
        tetris.pause();
        tetris=null;
        System.gc();
    }
}
