import javax.microedition.rms.RecordEnumeration;
import javax.microedition.rms.RecordStore;
import javax.microedition.rms.RecordStoreException;

public class rms extends Object {
 RecordStore rec;
 RecordEnumeration re;
 int num;
 String[] info;
 boolean[] changed;
 String name;
 public rms(String name, int num)
 {
  this.name=name;
  this.num=num;
  info = new String[num+1];
  changed = new boolean[num+1];
  info[0]="null";
 }

 public void LoadRms()
 {

  try {
   rec=RecordStore.openRecordStore(name,true);
   re = rec.enumerateRecords(null, null, false);
   //java.lang.System.out.println(Integer.toString(rec.getNumRecords()));
   for(int i=1; i<=num; i++)
   {
    if(i<=rec.getNumRecords() && rec.getRecordSize(i)!=0){info[i]=new String(rec.getRecord(i));}
    else{info[i]="null";}
    if(info[i]==null){info[i]="null";} changed[i]=false;
   }
   rec.closeRecordStore();
  }catch(RecordStoreException rse){java.lang.System.out.println("Load: error blin :(");}

 }

 public void SaveRms()
 {

  try {
   rec=RecordStore.openRecordStore(name,true);
   re = rec.enumerateRecords(null, null, false);
   for(int i=1; i<=num; i++)
   {
    //java.lang.System.out.print(Integer.toString(i)+": ");
    if(info[i]==null){info[i]="null";}
    if(i>rec.getNumRecords()){rec.addRecord(info[i].getBytes(),0,info[i].length()); continue;}
    if(changed[i]){rec.setRecord(i,info[i].getBytes(),0,info[i].length()); changed[i]=false;}
   }
   re.rebuild();
   rec.closeRecordStore();
  }catch(RecordStoreException rse){java.lang.System.out.println("Save: error blin :(");}

 }

 public void EditRms(int num, String prop)
 {
  info[num]=prop;
  changed[num]=true;
 }

 public String GetRms(int num, String prop)
 {
  if(info[num].equals("null")){info[num]=prop; return prop;}else{return info[num];}
 }

}