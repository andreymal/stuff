import javax.microedition.lcdui.*;

public class TetrisMenu extends Canvas {
    
    private rms r=new rms("amtetris_config",5);
    
    int keylsoft, keyrsoft, keyfire;
    public int
            //#if glamoor=="true"
//#            back=0xffbcdc,
//#            border=0xcf0092
            //#else
            back=0xcccccc,
            border=0x000000
            //#endif
            ;
    
    int curr=0;
    int lvl=1;
    int lines=0;
    int on3d=0;
    int sx=10;
    int sy=20;
    
    boolean go=false;
    
    AMTetris m;
    
    Font font = Font.getFont(Font.FACE_SYSTEM,Font.STYLE_PLAIN,Font.SIZE_SMALL);
    
    public TetrisMenu(AMTetris m){
         r.LoadRms();
         
         lvl=Integer.parseInt(r.GetRms(1,"1"));
         lines=Integer.parseInt(r.GetRms(2,"0"));
         on3d=Integer.parseInt(r.GetRms(3,"10"));
         sx=Integer.parseInt(r.GetRms(4,"10"));
         sy=Integer.parseInt(r.GetRms(5,"20"));
        
        
         this.m=m;
         setFullScreenMode(true);
         keylsoft=-6; keyrsoft=-7; keyfire=-5;
         try {
          Class.forName("com.siemens.mp.game.Light");
          keylsoft=-1; keyrsoft=-4;
          keyfire=-26;
         } catch (Exception e) {
         }

         try {
          Class.forName("com.motorola.funlight.FunLight");
          keylsoft=-21; keyrsoft=-22;
          keyfire=-20;
         } catch (Exception e) {
         }
    }
    
    protected void paint(Graphics g){
        g.setColor(back);
        g.fillRect(0,0,getWidth(),getHeight());
        g.setFont(font);
        g.setColor(border);
        
        if(go){
            go=false;
            g.drawString("Создание карты...",getWidth()/2,getHeight()/2,Graphics.TOP|Graphics.HCENTER);
            return;
        }
        
        String s = "Уровень "+Integer.toString(lvl);
        if(curr==0)s="< "+s+" >";
        g.drawString(s,getWidth()/2,getHeight()/6,Graphics.TOP|Graphics.HCENTER);
        
        s = "Заполненных линий "+Integer.toString(lines);
        if(curr==1)s="< "+s+" >";
        g.drawString(s,getWidth()/2,getHeight()*2/6,Graphics.TOP|Graphics.HCENTER);
        
        s = "Глубина 3D "+Integer.toString(on3d);
        if(curr==2)s="< "+s+" >";
        g.drawString(s,getWidth()/2,getHeight()*3/6,Graphics.TOP|Graphics.HCENTER);
        
        s = "Длина поля "+Integer.toString(sx);
        if(curr==3)s="< "+s+" >";
        g.drawString(s,getWidth()/2,getHeight()*4/6,Graphics.TOP|Graphics.HCENTER);
        
        s = "Высота поля "+Integer.toString(sy);
        if(curr==4)s="< "+s+" >";
        g.drawString(s,getWidth()/2,getHeight()*5/6,Graphics.TOP|Graphics.HCENTER);
        
        g.drawString("Начать",2,getHeight()-2,Graphics.BASELINE|Graphics.LEFT);
        g.drawString("Выйти",getWidth()-2,getHeight()-2,Graphics.BASELINE|Graphics.RIGHT);
        
    }
    
    public void keyPressed(int key){
        if(getGameAction(key)==DOWN){
            curr++;
        }
        if(getGameAction(key)==UP){
            curr--;
        }
        if(curr<0)curr=4;
        if(curr>4)curr=0;
        
        if(getGameAction(key)==LEFT){
            if(curr==0){
                lvl--;
                if(lvl<1)lvl=9;
            }else if(curr==1){
                lines--;
                if(lines<0)lines=15;
            }else if (curr==2){
                on3d-=2;
                if(on3d<0)on3d=98;
            }else if (curr==3){
                sx--;
                if(sx<5)sx=40;
            }else if (curr==4){
                sy--;
                if(sy<5)sy=40;
            }
        }else if(getGameAction(key)==RIGHT){
            if(curr==0){
                lvl++;
                if (lvl>9)lvl=1;
            }else if(curr==1){
                lines++;
                if (lines>15)lines=0;
            }else if (curr==2){
                on3d+=2;
                if(on3d>=98)on3d=0;
            }else if (curr==3){
                sx++;
                if(sx>40)sx=5;
            }else if (curr==4){
                sy++;
                if(sy>40)sy=5;
            }
        }
        
        if(key==keylsoft || key==keyfire){
            go=true;
            repaint();
            r.EditRms(1, Integer.toString(lvl));
            r.EditRms(2, Integer.toString(lines));
            r.EditRms(3, Integer.toString(on3d));
            r.EditRms(4, Integer.toString(sx));
            r.EditRms(5, Integer.toString(sy));
            r.SaveRms();
            m.startGame(sx,sy,lvl,lines,on3d);
            
        }
        if(key==keyrsoft){
            r.EditRms(1, Integer.toString(lvl));
            r.EditRms(2, Integer.toString(lines));
            r.EditRms(3, Integer.toString(on3d));
            r.EditRms(4, Integer.toString(sx));
            r.EditRms(5, Integer.toString(sy));
            r.SaveRms();
            m.destroyApp(false);    
        }
        
        repaint();
    }
    
    public void keyRepeated(int key){
        keyPressed(key);
    }
    
}
