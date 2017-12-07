/*
 * Copyright 2004 Grzegorz Grasza groz@gryf.info
 * 
 * This file is part of mobber. Mobber is free software; you can redistribute it
 * and/or modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of the License,
 * or (at your option) any later version. Mobber is distributed in the hope that
 * it will be useful, but WITHOUT ANY WARRANTY; without even the implied
 * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
 * General Public License for more details. You should have received a copy of
 * the GNU General Public License along with mobber; if not, write to the Free
 * Software Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
 * USA .
 */

package net;

import java.io.*;
import java.util.*;

/**
 * XML-Reader
 * 
 * @author Grzegorz Grasza
 * @version 1.0
 * @since 1.0
 */
public class XmlReader extends InputStreamReader {
	public final static int START_DOCUMENT = 0;

	public final static int END_DOCUMENT = 1;

	public final static int START_TAG = 2;

	public final static int END_TAG = 3;

	public final static int TEXT = 4;

	private Stack tags;

	private boolean inside_tag;

	private String tagName;

	private String text;

	private final Hashtable attributes = new Hashtable();

	private int c;

	private int type = START_DOCUMENT;

	public XmlReader(final InputStream in) throws IOException, UnsupportedEncodingException {
		super(in, "UTF-8");
		this.tags = new Stack();
		this.inside_tag = false;
	}

	public int next() throws IOException {
		this.c = this.read();
		if (this.c <= ' ') {
			while (((this.c = this.read()) <= ' ') && (this.c != -1)) {
				;
			}
		}
		if (this.c == -1) {

			this.type = END_DOCUMENT;
			return this.type;
		}

		if ((this.c == '<') || ((this.c == '/') && !this.inside_tag)) {
			this.inside_tag = true;
			// reset all
			this.tagName = null;
			this.text = null;
			this.attributes.clear();

			if (this.c == '<') {
				this.c = this.read();
			}
			if (this.c == '/') {
				this.type = END_TAG;
				this.c = this.read();
				this.tagName = this.readName('>');
			} else if ((this.c == '?') || (this.c == '!')) // ignore xml
															// heading &
															// comments
			{
				while ((this.c = this.read()) != '>') {
					;
				}
				this.next();
			} else {
				this.type = START_TAG;
				this.tagName = this.readName(' ');

				String attribute = "";
				String value = "";
				while (this.c == ' ') {
					this.c = this.read();
					attribute = this.readName('=');

					this.c = this.read(); // '''
					this.c = this.read();
					value = this.readText('\'');
					this.c = this.read();
					this.attributes.put(attribute, value);
				}
				if (this.c != '/') {
					this.inside_tag = false;
				}
			}
		} else if ((this.c == '>') && this.inside_tag) // last tag ended
		{
			this.type = END_TAG;
			this.inside_tag = false;
		} else {
			this.tagName = null;
			this.attributes.clear();

			this.type = TEXT;
			this.text = this.readText('<');
		}

		return this.type;
	}

	public int getType() {
		return this.type;
	}

	public String getName() {
		return this.tagName;
	}

	public String getAttribute(final String name) {
		return (String) this.attributes.get(name);
	}

	public Enumeration getAttributes() {
		return this.attributes.keys();
	}

	public String getText() {
		return this.text;
	}

	private String readText(final int end) throws IOException {
		final StringBuffer output = new StringBuffer("");
		while (this.c != end) {
			if (this.c == '&') {
				this.c = this.read();
				switch (this.c) {
					case 'l':
						output.append('<');
						break;
					case 'g':
						output.append('>');
						break;
					case 'a':
						if (this.read() == 'm') {
							output.append('&');
						} else {
							output.append('\'');
						}
						break;
					case 'q':
						output.append('"');
						break;
					case 'n':
						output.append(' ');
						break;
					default:
						output.append('?');
				}

				while ((this.c = this.read()) != ';') {
					;
				}
			} else if (this.c == '\\') {
				if ((this.c = this.read()) == '<') {
					break;
				} else {
					output.append((char) this.c);
				}
			} else {
				output.append((char) this.c);
			}
			this.c = this.read();
		}
		// while((c = read()) != end);
		return output.toString();
	}

	private String readName(final int end) throws IOException {
		final StringBuffer output = new StringBuffer("");
		do {
			output.append((char) this.c);
		} while (((this.c = this.read()) != end) && (this.c != '>') && (this.c != '/'));
		return output.toString();
	}
};
