package net;
import java.io.ByteArrayOutputStream;
import net.MD5;

public class Util {
    private ByteArrayOutputStream stream = new ByteArrayOutputStream();
    public byte[] toByteArray() {
        return stream.toByteArray();
    }

    public void writeByte(int value) {
        try {
            stream.write(value);
        } catch (Exception e) {
        }
    }

    public void writeByteArray(byte[] array) {
        try {
            stream.write(array);
        } catch (Exception e) {
        }
    }
    
    public void writeByteArray(byte[] array, int offset, int length) {
        try {
            stream.write(array, offset, length);
        } catch (Exception e) {
        }
    }

    private static final String base64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=";
    private static final int base64GetNextChar(String str, int index) {
        if (-1 == index) return -2;
        char ch = str.charAt(index);
        if ('=' == ch) {
            return -1;
        }
        return base64.indexOf(ch);
    }
    private static final int base64GetNextIndex(String str, int index) {
        for (; index < str.length(); ++index) {
            char ch = str.charAt(index);
            if ('=' == ch) {
                return index;
            }
            int code = base64.indexOf(ch);
            if (-1 != code) {
                return index;
            }
        }
        return -1;
    }
    
    public static final byte[] base64decode(String str) {
        if (null == str) str = "";
        Util out = new Util();
        for (int strIndex = 0; strIndex < str.length(); ++strIndex) {
    	    strIndex = base64GetNextIndex(str, strIndex);
            int ch1 = base64GetNextChar(str, strIndex);

            strIndex = base64GetNextIndex(str, strIndex + 1);
            if (-1 == strIndex) break;
            int ch2 = base64GetNextChar(str, strIndex);
            if (-1 == ch2) break;
            out.writeByte((byte)(0xFF & ((ch1 << 2) | (ch2 >>> 4))));

            strIndex = base64GetNextIndex(str, strIndex + 1);
            if (-1 == strIndex) break;
            int ch3 = base64GetNextChar(str, strIndex);
            if (-1 == ch3) break;
            out.writeByte((byte)(0xFF & ((ch2 << 4) | (ch3 >>> 2))));

            strIndex = base64GetNextIndex(str, strIndex + 1);
            if (-1 == strIndex) break;
            int ch4 = base64GetNextChar(str, strIndex);
            if (-1 == ch4) break;
            out.writeByte((byte)(0xFF & ((ch3 << 6) | (ch4 >>> 0))));
        }
        return out.toByteArray();
    }
    public static final String base64encode( final byte[] data ) {
        char[] out = new char[((data.length + 2) / 3) * 4];
        for (int i = 0, index = 0; i < data.length; i += 3, index += 4) {
            boolean quad = false;
            boolean trip = false;
            
            int val = (0xFF & data[i]);
            val <<= 8;
            if ((i + 1) < data.length) {
                val |= (0xFF & data[i+1]);
                trip = true;
            }
            val <<= 8;
            if ((i + 2) < data.length) {
                val |= (0xFF & data[i+2]);
                quad = true;
            }
            out[index+3] = base64.charAt(quad ? (val & 0x3F) : 64);
            val >>= 6;
            out[index+2] = base64.charAt(trip ? (val & 0x3F) : 64);
            val >>= 6;
            out[index+1] = base64.charAt(val & 0x3F);
            val >>= 6;
            out[index+0] = base64.charAt(val & 0x3F);
        }
        return new String(out);
    }

    /**
     * This routine generates MD5-DIGEST response via SASL specification
     * (From BOMBUS project)
     *
     * @param user
     * @param pass
     * @param realm
     * @param digest_uri
     * @param nonce
     * @param cnonce
     * @return
     */
    public static String responseMd5Digest(String user, String pass,
            String realm, String digestUri, String nonce, String cnonce) {
        MD5 hUserRealmPass = new MD5();
        hUserRealmPass.init();
        hUserRealmPass.updateASCII(user);
        hUserRealmPass.update((byte) ':');
        hUserRealmPass.updateASCII(realm);
        hUserRealmPass.update((byte) ':');
        hUserRealmPass.updateASCII(pass);
        hUserRealmPass.finish();
        
        MD5 hA1 = new MD5();
        hA1.init();
        hA1.update(hUserRealmPass.getDigestBits());
        hA1.update((byte) ':');
        hA1.updateASCII(nonce);
        hA1.update((byte) ':');
        hA1.updateASCII(cnonce);
        hA1.finish();
        
        MD5 hA2 = new MD5();
        hA2.init();
        hA2.updateASCII("AUTHENTICATE:");
        hA2.updateASCII(digestUri);
        hA2.finish();
        
        MD5 hResp = new MD5();
        hResp.init();
        hResp.updateASCII(hA1.getDigestHex());
        hResp.update((byte) ':');
        hResp.updateASCII(nonce);
        hResp.updateASCII(":00000001:");
        hResp.updateASCII(cnonce);
        hResp.updateASCII(":auth:");
        hResp.updateASCII(hA2.getDigestHex());
        hResp.finish();
        
        return Util.base64encode(
                new StringBuffer()
                .append("username=\"").append(user)
                .append("\",realm=\"").append(realm)
                .append("\",nonce=\"").append(nonce)
                .append("\",nc=00000001,cnonce=\"").append(cnonce)
                .append("\",qop=auth,digest-uri=\"").append(digestUri)
                .append("\",response=\"").append(hResp.getDigestHex())
                .append("\",charset=utf-8").toString().getBytes());
    }

    public static final String replace(String text, String from, String to) {
        int fromSize = from.length();
        int toSize = to.length();
        int pos = 0;
        for (;;) {
            pos = text.indexOf(from, pos);
            if (pos == -1) break;
            text = text.substring(0, pos) + to
                    + text.substring(pos + fromSize, text.length());
            pos += toSize;
        }
        return text;
    }
    
    public static final String replace(String text, String[] from, String[] to, String keys) {
        // keys - is first chars of from
        StringBuffer result = new StringBuffer();
        int pos = 0;
        while (pos < text.length()) {
            char ch = text.charAt(pos);

            int index = keys.indexOf(ch);
            while (-1 != index) {
                if (text.startsWith(from[index], pos)) {
                    pos += from[index].length();
                    result.append(to[index]);
                    break;
                }
                index = keys.indexOf(text.charAt(pos), index + 1);
            }

            if (-1 == index) {
                result.append(ch);
                pos++;
            }
        }
        
        return result.toString();
    }

}
