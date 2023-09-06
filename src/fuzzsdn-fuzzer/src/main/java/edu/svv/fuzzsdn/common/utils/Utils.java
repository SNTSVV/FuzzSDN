package edu.svv.fuzzsdn.common.utils;


public class Utils
{
    final protected static char[] HEX_CHAR = "0123456789ABCDEF".toCharArray();


    /**
     * Transform byte array to human readable HEX byte string
     *
     * @param byte_array array of bytes
     * @return a string of HEX characters
     */
    public static String bytesToHex(byte[] byte_array)
    {
        StringBuilder sb = new StringBuilder();

        for (int i = 0; i < byte_array.length; i++)
            sb.append(String.format("%02X%s", byte_array[i], (i < byte_array.length - 1) ? " " : ""));

        return sb.toString();
    }

    /**
     * Indicate if a String is null or is empty
     *
     * @param s input string
     * @return boolean whether indicating whether the string is null or empty
     */
    public static boolean isNullOrEmpty(String s)
    {
        return s == null || s.isBlank();
    }

    /**
     * Transform a MAC string to a byte array
     *
     * @param mac The MAC address as a string
     * @return The MAC address as a byte array
     */
    public static byte[] macStringToBytes(String mac)
    {
        String[] macAddressParts = mac.split(":");

        // convert hex string to byte values
        byte[] macAddressBytes = new byte[6];
        for (int i = 0; i < 6; i++)
        {
            int hex = Integer.parseInt(macAddressParts[i], 16);
            macAddressBytes[i] = (byte) hex;
        }

        return macAddressBytes;
    }

    /**
     * Transform a MAC byte array to a string
     *
     * @param mac The MAC address as a byte array
     * @return The MAC address as a string
     */
    public static String macBytesToString(byte[] mac)
    {
        StringBuilder sb = new StringBuilder(18);
        for (byte b : mac)
        {
            if (sb.length() > 0)
                sb.append(':');
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
