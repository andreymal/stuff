package net;

import java.io.*;
import java.util.*;

//import com.jcraft.jzlib.ZOutputStream;
//import com.jcraft.jzlib.JZlib;

/**
 * XML-Writer
 * 
 * @author Grzegorz Grasza
 * @version 1.0
 * @since 1.0
 */
public class XmlWriter extends OutputStreamWriter {
	Stack tags;

	boolean inside_tag;

	public XmlWriter(final OutputStream out) throws UnsupportedEncodingException {
		super(out, "UTF-8");
		this.tags = new Stack();
		this.inside_tag = false;
		//((ZOutputStream)out).setFlushMode(JZlib.Z_SYNC_FLUSH);
	}

	public void flush() throws IOException {
		if (this.inside_tag) {
			this.write('>'); // prevent Invalid XML fatal error
			this.inside_tag = false;
		}
		super.flush();
	}

	public void startTag(final String tag) throws IOException {
		if (this.inside_tag) {
			this.write('>'); this.write('<');
		} else {
		this.write(' ');
		this.write('<'); }
		this.write(tag);
		this.tags.push(tag);
		this.inside_tag = true;
	}

	public void attribute(final String atr, final String value) throws IOException {
		if (value == null) { return; }
		this.write(' ');
		this.write(atr);
		this.write("=\'");
		this.writeEscaped(value);
		this.write('\'');
	}

	public void endTag() throws IOException {
		try {
			final String tagname = (String) this.tags.pop();
			if (this.inside_tag) {
				this.write("/>");
				this.inside_tag = false;
			} else {
				this.write("</");
				this.write(tagname);
				this.write('>');
			}
		} catch (final EmptyStackException e) {
		}
	}

	public void text(final String str) throws IOException {
		if (this.inside_tag) {
			this.write('>');
			this.inside_tag = false;
		}
		this.writeEscaped(this.encodeUTF(str));
	}

	private void writeEscaped(final String str) throws IOException {
		final int index = 0;
		for (int i = 0; i < str.length(); i++) {
			final char c = str.charAt(i);
			switch (c) {
				case '<':
					this.write("&lt;");
				case '>':
					this.write("&gt;");
				case '&':
					this.write("&amp;");
				case '\'':
					this.write("&apos;");
				case '"':
					this.write("&quot;");
				default:
					this.write(c);
			}
		}
	}

 public String getXml() {return tags.toString();}


	private String encodeUTF(final String str) {
		try {
			final String utf = new String(str.getBytes("UTF-8"), "UTF-8");
			return utf;
		} catch (final UnsupportedEncodingException e) {
			return null;
		}
	}
};
