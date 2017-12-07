import java.util.Calendar;
import java.util.Random;
import java.util.Timer;
import java.util.TimerTask;
import javax.microedition.lcdui.Canvas;
import javax.microedition.lcdui.Font;
import javax.microedition.lcdui.Graphics;

public class TetrisCanv extends Canvas{
    AMTetris ml;
    
    int on3d;
    
    int oklines=0;
    int[] lvls={500,430,360,300,300,250,210,160,100};
    
    private rms r=new rms("amtetris_best",1);
    
    Calendar cl = Calendar.getInstance();
    int s=0;
    byte day=0;
    boolean block2=false;
    
    private int best=0;
    
    int keylsoft,keyrsoft,keyfire;
    
    private int key=Integer.MAX_VALUE;
    
    public int
            //#if glamoor=="true"
//#            back=0xffbcdc,
//#            border=0xcf0092
            //#else
            back=0xcccccc,
            border=0x000000
            //#endif
            ;
    public static final int[] colors={0x000000,0xff3333,0x00ff00,0xeeee00,0x5555ff
            //#if glamoor=="true"
//#             ,0xc900a0,0xf900b0
            //#endif
    };
    public int[][] colors_face;
    public int[][] map;
    
    private int[][] pausemap;
    
    public int sx, sy, w=0, h=0, k=0,c=1, balls=0, lvl=1;
    private long time=500;
    
    private boolean block_key=false;
    
    //private int koef=90;
    
    private boolean keyed=false, gameover=false, paused=false;
    
    Font font = Font.getFont(Font.FACE_SYSTEM,Font.STYLE_PLAIN,Font.SIZE_SMALL);
    
    //<editor-fold defaultstate="collapsed" desc="Массив с фигурами">
    public int[][][][] figures={
        //Z1
        {
            {
                {0,0},
                {0,1},
                {1,1},
                {1,2}
            },
            {
                {2,0},
                {1,0},
                {1,1},
                {0,1}
            }
        },
        //Кубик
        {
            {
                {0,0},
                {0,1},
                {1,0},
                {1,1}
            }
        },
        //T
        {
            {
                {1,0},
                {0,1},
                {1,1},
                {2,1}
            },
            {
                {1,0},
                {1,1},
                {1,2},
                {2,1}
            },
            {
                {0,1},
                {1,1},
                {2,1},
                {1,2}
            },
            {
                {1,0},
                {1,1},
                {1,2},
                {0,1}
            }
                
                /*{
                 * {1,1},
                 * {0,2},
                 * {1,2},
                 * {2,2}
                 * },
                 * {
                 * {2,0},
                 * {2,1},
                 * {1,1},
                 * {2,2}
                 * },
                 * {
                 * {0,0},
                 * {1,0},
                 * {2,0},
                 * {1,1}
                 * },
                 * 
                 * {
                 * {0,0},
                 * {0,1},
                 * {1,1},
                 * {0,2}
                 * }
                 */},
        //палка
        {
            {
                {1,0},
                {1,1},
                {1,2},
                {1,3}
            },
            {
                {0,1},
                {1,1},
                {2,1},
                {3,1}
            }
        },
        
        //Z2
        {
            {
                {1,0},
                {0,1},
                {1,1},
                {0,2}
            },
            {
                {2,1},
                {1,0},
                {1,1},
                {0,0}
            }
        },
        //Г
        {
            {
                {1,0},
                {2,0},
                {1,1},
                {1,2}
            },
            {
                {0,1},
                {1,1},
                {2,1},
                {2,2}
            },
            {
                {1,0},
                {1,1},
                {1,2},
                {0,2}
            },
            {
                {0,0},
                {0,1},
                {1,1},
                {2,1}
            }
        },
        //L
        {
            {
                {0,0},
                {1,0},
                {1,1},
                {1,2}
            },
            {
                {0,1},
                {1,1},
                {2,1},
                {2,0}
            },
            {
                {1,0},
                {1,1},
                {1,2},
                {2,2}
            },
            {
                {0,1},
                {1,1},
                {2,1},
                {0,2}
            }
        }
    };
    //</editor-fold>
    
    private Timer timer;
    private TimerTask tk;
    Random random = new Random();
    private int current,next, cx, cy, rot, col, nextcol, nextrot;
    
    private boolean check(int x, int y){
      if ( map[x][y]!=0 ){
        return true;
      }
      return false;
    }
    
    private boolean delete_lines(){
        boolean ok;
        for(int i=sy-1;i>=0;i--){
            ok=true;
            for(int xx=0;xx<sx;xx++){
                if(map[xx][i]==0){ok=false;break;}
            }
            //System.out.print(i);
            //System.out.println(ok);
            if(!ok)continue;
            for(int z=i-1;z>=0;z--){
                for(int zz=0;zz<sx;zz++)map[zz][z+1]=map[zz][z];
            }
            //for (int ii=0;ii<sx;ii++)map[ii][0]=0;
            return true;
        }
        return false;
    }
    
    private boolean touch(){
        
        for(int i=0;i<figures[current][rot].length;i++){
            if(figures[current][rot][i][0]+cx<0 || figures[current][rot][i][0]+cx>=sx)return true;
            if(figures[current][rot][i][1]+cy<0 || figures[current][rot][i][1]+cy>=sy)return true;
            if(check(figures[current][rot][i][0]+cx, figures[current][rot][i][1]+cy)){return true;}
        }
        return false;
    }
    
    private void repaint_figur(int color){
        for(int i=0;i<figures[current][rot].length;i++){
            map[figures[current][rot][i][0]+cx][figures[current][rot][i][1]+cy]=color;
        }
    }
    
    public void create_timer(long l){
        System.gc();
        tk=new TimerTask(){public void run(){
         while(block2){System.out.println("oops");}
         block_key=true;
         //for(int i=0;i<1000000;i++){}
         if(!keyed){
         repaint_figur(0);
         
         cy++;
         if(touch()){
             cy--;
             repaint_figur(col);
             int d=0;
             while(delete_lines()){d++;}
             oklines+=d;
             if(d==1)balls+=100;
             else if(d==2)balls+=300;
             else if(d==3)balls+=700;
             else if(d==4)balls+=1500;
             else if(d>2)balls=-666;
             balls+=figures[current][rot].length;
             cx=sx/2-1;
             cy=0;
             current=next;
             col=nextcol;
             nextcol=Math.abs( random.nextInt() ) % (colors.length-1)+1;
             next=Math.abs( random.nextInt() ) % figures.length;
             //next=3;
             rot=nextrot;
             nextrot=Math.abs( random.nextInt() ) % figures[next].length;
             
             boolean norm=true;
             for (int xx=0;xx<sx;xx++){
                 if (map[xx][0]!=0){norm=false;break;}
             }
             if(!touch() && norm)repaint_figur(col);
             else{
                 gameover=true;
                 if(balls>best){
                     best=balls;
                     r.EditRms(1, Integer.toString(best));
                     r.SaveRms();
                 }
                 timer.cancel();
             }
             
             /*int lvl1=balls/1375+1;
             if(lvl1>9)lvl1=9;*/
             if (oklines>=10){
                 oklines-=10;
                 lvl++;
                 if(lvl>lvls.length)lvl=lvls.length;
                 //System.out.println("levelup");
                 //repaint();
                 time=lvls[lvl-1];
                 timer.cancel();
                 create_timer(0);
             }
           
         }else{
             repaint_figur(col);
         }
         }keyed=false;
        block_key=false;
        if(key!=Integer.MAX_VALUE){keyPressed(key);key=Integer.MAX_VALUE;}
        repaint();}};
        
        timer=new Timer();
        timer.schedule(tk,l,time);
    }
    
    private void myinit(final int sx, final int sy, final int lvl, final int blines){
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
        
        
        r.LoadRms();
        if(
                cl.get(Calendar.MONTH)==11 && cl.get(Calendar.DAY_OF_MONTH)>=25 ||
                cl.get(Calendar.MONTH)==0 && cl.get(Calendar.DAY_OF_MONTH)<=13
          )day=1;
        //#if personal_birthday_edition=="true"
        //if(
        //        cl.get(Calendar.MONTH)==N/A && cl.get(Calendar.DAY_OF_MONTH)==N/A
        //  )day=2;
        //#endif
        
        best=Integer.parseInt(r.GetRms(1,"0"));
        
        colors_face=new int[4][colors.length];
        for (int i=0;i<colors.length;i++){
            //int clr=colors[];
            byte c1=(byte)(colors[i]/0x010000);
            byte c2=(byte)(colors[i]/0x000100%0x010000);
            byte c3=(byte)(colors[i]%0x000100);
            colors_face[0][i]=
                    (int)(c1&0xff)*60/100*0x010000+
                    (int)(c2&0xff)*60/100*0x000100+
                    (int)(c3&0xff)*60/100;
            colors_face[1][i]=
                    (int)(c1&0xff)*70/100*0x010000+
                    (int)(c2&0xff)*70/100*0x000100+
                    (int)(c3&0xff)*70/100;
            colors_face[2][i]=
                    (int)(c1&0xff)*55/100*0x010000+
                    (int)(c2&0xff)*55/100*0x000100+
                    (int)(c3&0xff)*55/100;
            colors_face[3][i]=
                    (int)(c1&0xff)*50/100*0x010000+
                    (int)(c2&0xff)*50/100*0x000100+
                    (int)(c3&0xff)*50/100;
        }
        
        keyed=false;gameover=false;paused=false;
        time=lvls[lvl-1];
        w=0; h=0; k=0;c=1; balls=0; this.lvl=lvl;
        setFullScreenMode(true);
        this.sx=sx;this.sy=sy;
        map=new int[sx][sy];
        pausemap=new int[sx][sy];
        for(int x=0;x<sx;x++)for(int y=0;y<sy;y++){
            pausemap[x][y]=0;
            if(y<sy-blines)map[x][y]=0;
            else{
                map[x][y]=Math.abs(random.nextInt())%(colors.length);
                if(map[x][y]!=0)map[x][y]=Math.abs(random.nextInt())%(colors.length);
                if(x==sx-1){
                    boolean ok=false;
                    for(int i=0;i<sx;i++){
                        if(map[i][y]==0){ok=true;break;}
                    }
                    if(!ok)map[Math.abs(random.nextInt())%(sx)][y]=0;
                }
            }
        }
        
        
        if(day!=2){
        if(sx>=9 && sy>=14){
            int z=colors.length-1;
            pausemap[3][6]=z;
            pausemap[3][7]=z;
            pausemap[3][8]=z;
            pausemap[3][9]=z;
            pausemap[6][6]=z;
            pausemap[6][7]=z;
            pausemap[6][8]=z;
            pausemap[6][9]=z;
            
            pausemap[3][13]=z;
            pausemap[4][13]=z;
            pausemap[5][13]=z;
            pausemap[6][13]=z;
            
            pausemap[2][12]=z;
            pausemap[1][11]=z;
            pausemap[7][12]=z;
            pausemap[8][11]=z;
        }
        }
        
        create_timer(time);
        
        current=Math.abs( random.nextInt() ) % figures.length;
        next=Math.abs( random.nextInt() ) % figures.length;
        //current=3;next=3;
        
        col=Math.abs( random.nextInt() ) % (colors.length-1)+1;
        nextcol=Math.abs( random.nextInt() ) % (colors.length-1)+1;
        cx=sx/2-1;
        cy=0;
        rot=Math.abs( random.nextInt() ) % figures[current].length;
        nextrot=Math.abs( random.nextInt() ) % figures[next].length;
        repaint_figur(col);
    }
    
    public TetrisCanv(AMTetris ml, int on3d, final int sx, final int sy, final int lvl, final int blines){
        this.ml=ml;
        this.on3d=on3d;
        myinit(sx,sy,lvl, blines);
    }
    
    private void resize(int ww, int hh){
        w=ww;h=hh;
        k=w/(sx+7);
        if (h/(sy+2)<k)k=h/(sy+2);
        if(k<1)k=1;
    }
    
    protected void paint(Graphics g){
        /*if(painting==1){
            //System.out.println("paint");
            g.setColor(0x00ff00);
            g.fillRect(0,0,k,k);
            painting=0;return;
        }else if (painting==2){
            g.setColor(0xff0000);
            g.fillRect(0,0,k,k);
            painting=0;return;
        }*/
        
        g.setFont(font);
        g.setColor(back);
        g.fillRect(0,0,getWidth(),getHeight());
        g.setColor(border);
        
        g.drawString("Пауза",2,getHeight()-2,Graphics.BASELINE|Graphics.LEFT);
        g.drawString("Выйти",getWidth()-2,getHeight()-2,Graphics.BASELINE|Graphics.RIGHT);
        
        if (w!=getWidth() || h!=getHeight())resize(getWidth(),getHeight());
        
        if(day==1 || day==2){
            if(day==1)g.setColor(0xffffff);
            else if (day==2)g.setColor(0xff4444);
            int x=s;
            while(x>=4)x-=4;
            byte o=0;
            int z=k*4;
            for(int i=-z*2;i<h;i+=z){
                for(int j=-z*2;j<w;j+=z){
                    if(x==0 || x==2)g.drawString("*", j+z/2*o, i+z*s/8, 0);
                    else if(x==1)g.drawString("*", j-z/6+z/2*o, i+z*s/8, 0);
                    else if(x==3)g.drawString("*", j+z/6+z/2*o, i+z*s/8, 0);
                }
                o+=1;
                if(o>=2)o=0;
            }
            s+=1;
            if(s>=16)s=0;
        }
        
        /*if(h>k*22){
            g.translate(0, (h-k*22)/2);
        }else if (w>k*17){
            g.translate((w-k*17)/2, 0);
        }*/
        g.translate((w-k*(sx+7))/2, 0);
        
        //koef--;
        //if(koef<=0)koef=1;
        //koef=90;
        //if(on3d){
        int ww=w;
        int hh=h;
        int kx=ww*(100-on3d)/200;
        int ky=hh*(100-on3d)/200;
        //koef=100;
        //int kx=0;int ky=0;
        //}
        int[][] m;
        if(!paused)m=map;
        else m=pausemap;
        if(on3d>0){
        for(int x=0;x<sx;x++)for(int y=0;y<sy;y++){
            if(m[x][y]==0)continue;
            /*int clr=colors[map[x][y]];
            byte c1=(byte)(clr/0x010000);
            byte c2=(byte)(clr/0x000100%0x010000);
            byte c3=(byte)(clr%0x000100);*/
            
            int x1=(k*(x+1))*on3d/100+kx; int y1=(k*(y+1))*on3d/100+ky;
            int x2=(k*(x+1)+k)*on3d/100+kx; int y2=(k*(y+1))*on3d/100+ky;
            int x3=(k*(x+1)+k)*on3d/100+kx; int y3=(k*(y+1)+k)*on3d/100+ky;
            int x4=(k*(x+1))*on3d/100+kx; int y4=(k*(y+1)+k)*on3d/100+ky;
            
            //(int)(c1&0xff)*60/100*0x010000+(int)(c2&0xff)*60/100*0x000100+(int)(c3&0xff)*60/100
            
            //верхняя грань
            if(y>0 && m[x][y-1]==0 && y1>=hh/2){
                g.setColor(colors_face[0][m[x][y]]);
                //g.setColor((int)(c1&0xff)*60/100*0x010000+(int)(c2&0xff)*60/100*0x000100+(int)(c3&0xff)*60/100);
                g.fillTriangle(x1, y1, x2, y2, k*(x+1)+k, k*(y+1));
                g.fillTriangle(k*(x+1), k*(y+1), x1, y1, k*(x+1)+k, k*(y+1));
            }
            
            //правая грань
            if(x<sx-1 && m[x+1][y]==0 && x2<=ww/2){
                g.setColor(colors_face[1][m[x][y]]);
                //g.setColor((int)(c1&0xff)*70/100*0x010000+(int)(c2&0xff)*70/100*0x000100+(int)(c3&0xff)*70/100);
                g.fillTriangle(x2, y2, x3, y3, k*(x+1)+k, k*(y+1)+k);
                g.fillTriangle(x2, y2, k*(x+1)+k, k*(y+1), k*(x+1)+k, k*(y+1)+k);
            }
            
            //нижняя грань
            
            if(y<sy-1 && m[x][y+1]==0 && y3<=hh/2){
                g.setColor(colors_face[2][m[x][y]]);
                //g.setColor((int)(c1&0xff)*55/100*0x010000+(int)(c2&0xff)*55/100*0x000100+(int)(c3&0xff)*55/100);
                g.fillTriangle(x3, y3, x4, y4, k*(x+1), k*(y+1)+k);
                g.fillTriangle(x3, y3, k*(x+1)+k, k*(y+1)+k, k*(x+1), k*(y+1)+k);
            }
            
            //левая грань
            if(x>0 && m[x-1][y]==0 && x4>=ww/2){
                g.setColor(colors_face[3][m[x][y]]);
                //g.setColor((int)(c1&0xff)*50/100*0x010000+(int)(c2&0xff)*50/100*0x000100+(int)(c3&0xff)*50/100);
                g.fillTriangle(x4, y4, x1, y1, k*(x+1), k*(y+1));
                g.fillTriangle(x4, y4, k*(x+1), k*(y+1)+k, k*(x+1), k*(y+1));
            }
        }
        }
        for(int x=0;x<sx;x++)for(int y=0;y<sy;y++){
            if(m[x][y]==0)continue;
            g.setColor(colors[m[x][y]]);
            g.fillRect((k*(x+1)),(k*(y+1)),(k),(k));
            
        }
        
        g.setColor(border);
        g.drawRect(k*(sx+2)-1,k-1,k*4+1,k*4+1);
        if(!paused){
        g.setColor(colors[nextcol]);
        for(int i=0;i<figures[next][0].length;i++){
            g.fillRect(k*(sx+2)+k*figures[next][nextrot][i][0],k+k*figures[next][nextrot][i][1],k,k);
        }
        }
        g.setColor(border);
        g.drawString(Integer.toString(balls),k*(sx+2),k*6,0);
        g.drawString("Уровень "+Integer.toString(lvl),k*(sx+2),k*6+font.getHeight()+5,0);
        
        g.drawString("Лучший:",k*(sx+2),k*6+font.getHeight()*3+5,0);
        g.drawString(Integer.toString(best),k*(sx+2),k*6+font.getHeight()*4+5,0);
        
        
        
        if(gameover)g.drawString("Конец игры!",k,k,0);
        //if(gameover)g.drawString("Нажмите 5",k,k+font.getHeight()+5,0);
        else if (paused)
            //#if personal_birthday_edition=="true"
            if(day==2)
                g.drawString("Happy brithday",k,k,0);
            else
            //#endif
                g.drawString("Пауза",k,k,0);
        g.setColor(border);
        g.drawRect((k-1), (k-1), (k*sx+1), (k*sy+1));
        
        /*if(w<h){
            g.translate(0, -(h-k*22)/2);
        }else if (w>h){
            g.translate(-(w-k*17)/2,0);
        }*/
        g.translate(-(w-k*(sx+7))/2, 0);
    }
    
    public void pause(){
        timer.cancel();
        paused=true;
    }
    public void unpause(){
        create_timer(0);
        paused=false;
    }
    
    public void keyPressed(int key){
        block2=true;
        /*if (getGameAction(key)==GAME_C || key==KEY_NUM7){
            koef-=2;
            if (koef<2)koef=2;
            repaint();
        }else if (getGameAction(key)==GAME_D || key==KEY_NUM9){
            koef+=2;
            if(koef>100)koef=100;
            repaint();
        }*/
        if(block_key){this.key=key;block2=false;return;}
        if (getGameAction(key)==LEFT && !gameover && !paused){
            repaint_figur(0);
            cx--;
            if(touch())cx++;
            repaint_figur(col);
        }else if (getGameAction(key)==RIGHT && !gameover && !paused){
            repaint_figur(0);
            cx++;
            if(touch())cx--;
            repaint_figur(col);
        }else if ((key==keyfire || getGameAction(key)==DOWN) && !gameover && !paused){
            int oldcy=cy;
            repaint_figur(0);
            int d=0;
            while(!touch()){cy++;d++;}
            cy--;
            repaint_figur(col);
            balls+=d-1;
            if(cy!=oldcy)keyed=true;
        }else if (getGameAction(key)==UP && !gameover && !paused){
            repaint_figur(0);
            int oldrot=rot;
            rot++;
            if (rot>=figures[current].length)rot=0;
            if(touch())rot=oldrot;
            repaint_figur(col);
        /*}else if (gameover && (key==keyfire || key==KEY_NUM5 || getGameAction(key)==FIRE)){
            myinit(sx, sy, 1);
            repaint();
        */}else if ((key==keylsoft || key==KEY_STAR || getGameAction(key)==GAME_A) && !gameover){
            if(paused)unpause();
            else pause();
        }else if (key==keyrsoft){
            ml.stopGame();
        }
        repaint();block2=false;
    }
}
