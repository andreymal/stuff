/*
 * Copyright 2006 Swen Kummer, Dustin Hass, Sven Jost
 * http://jxa.sourceforge.net/
 * 
 * This is free software; you can redistribute it and/or modify it under the
 * terms of the GNU General Public License as published by the Free Software
 * Foundation; either version 2 of the License, or (at your option) any later
 * version. Mobber is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
 * details. You should have received a copy of the GNU General Public License
 * along with mobber; if not, write to the Free Software Foundation, Inc., 59
 * Temple Place, Suite 330, Boston, MA 02111-1307 USA .
 */

package net;

public interface XmppListener {
 public void onConnFailed(final int accnum);
 public void onAuth(final int accnum);
 public void onAuthFailed(final int accnum, final String message);
 public void onIqFailed(final int accnum, final String type, final String id, final String code);
 public void onMessageEvent(final int accnum, final String from, final String resource, final String type, final String subject, final String body);
 public void onContactRemoveEvent(final int accnum, final String jid);
 public void onContactEvent(final int accnum, final String jid, final String name, final String group, final String subscription);
 public void onStatusEvent(final int accnum, final String jid, final String show, final String status);
 public void onSubscribeEvent(final int accnum, final String jid);
 public void onUnsubscribeEvent(final int accnum, final String jid);
 public void onXml(final int accnum, final boolean out, final String code);
 public void onRegister();
 public void onRegisterFailed(final String code);
 public void onRemoved(final int accnum);
 public void onRemoveFailed(final int accnum);
 public void onOfflineEvent(final int accnum, final String jid, final String status);
 //public void onDiscoItem(final int accnum, final String from, final String itemjid,final String itemname, final String id);
 //public void onDiscoFeature(final int accnum, final String from, final String feature, final String id);
 public void onAddBook(final int accnum, final String autojoin, final String name, final String jid, final String nick);
 //для отладки
 public void onStep(int step);

 public void netPanic(String panic);

 //public void onModuleParse(String command, String p1, String p2, String p3, String p4, String p5, String p6, String p7, String p8); 
};
