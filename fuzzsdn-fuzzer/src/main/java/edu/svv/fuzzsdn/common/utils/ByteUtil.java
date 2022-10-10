package edu.svv.fuzzsdn.common.utils;

import java.math.BigInteger;
import java.util.Arrays;
import java.util.Random;

public class ByteUtil
{

    protected static Random RANDOM = new Random();

    /**
     * The regular {@link java.math.BigInteger#toByteArray()} method isn't quite what we often need:
     * it appends a leading zero to indicate that the number is positive and may need padding.
     *
     * @param b the integer to format into a byte array
     * @param numBytes the desired size of the resulting byte array
     * @return numBytes byte long array.
     */
    public static byte[] bigIntegerToBytes(BigInteger b, int numBytes)
    {
        if (b == null)
            return null;
        byte[] bytes = new byte[numBytes];
        byte[] biBytes = b.toByteArray();
        int start = (biBytes.length == numBytes + 1) ? 1 : 0;
        int length = Math.min(biBytes.length, numBytes);
        System.arraycopy(biBytes, start, bytes, numBytes - length, length);
        return bytes;
    }

    /**
     * Omitting sign indication byte. We use this custom method to avoid an empty array in case of BigInteger.ZERO
     *
     * @param value - any big integer number. A {@code null}-value will return {@code null}
     * @return A byte array without a leading zero byte if present in the signed encoding.
     *      BigInteger.ZERO will return an array with length 1 and byte-value 0.
     */
    public static byte[] bigIntegerToBytes(BigInteger value)
    {
        if (value == null)
            return null;

        byte[] data = value.toByteArray();

        if (data.length != 1 && data[0] == 0) {
            byte[] tmp = new byte[data.length - 1];
            System.arraycopy(data, 1, tmp, 0, tmp.length);
            data = tmp;
        }
        return data;
    }


    public static byte[] bigIntegerToBytesSigned(BigInteger b, int numBytes)
    {
        if (b == null)
            return null;
        byte[] bytes = new byte[numBytes];
        Arrays.fill(bytes, b.signum() < 0 ? (byte) 0xFF : 0x00);
        byte[] biBytes = b.toByteArray();
        int start = (biBytes.length == numBytes + 1) ? 1 : 0;
        int length = Math.min(biBytes.length, numBytes);
        System.arraycopy(biBytes, start, bytes, numBytes - length, length);
        return bytes;
    }

    /**
     * Generate a random {@link BigInteger} between two bounds.
     * @param min the minimum value
     * @param max the maximum value
     * @return a random number between {@code min} and {@code max}
     */
    // Generates a random integer in [min, max]
    public static BigInteger randomBigInteger(BigInteger min, BigInteger max)
    {
        if(max.compareTo(min) < 0)
        {
            BigInteger tmp = min;
            min = max;
            max = tmp;
        }
        else if (max.compareTo(min) == 0)
        {
            return min;
        }

        max = max.add(BigInteger.ONE);
        BigInteger range = max.subtract(min);
        int length = range.bitLength();
        BigInteger result;
        do
        {
            result = new BigInteger(length, RANDOM);
        } while(result.compareTo(range) >= 0);

        result = result.add(min);
        return result;
    }


    /**
     * Calculate the logarithm scale 2 of a {@link BigInteger}.
     * @param val the big integer
     * @return the log2 of the input value.
     * @throws ArithmeticException when the value is <= to 0
     */
    public static double log2(BigInteger val)
    {
        // The log2 of a number <= 0 is undefined
        if (val.compareTo(BigInteger.ZERO) <= 0)
            throw new ArithmeticException("Log2 of " + val.toString() + " is undefined");

        // Get the minimum number of bits necessary to hold this value.
        int n = val.bitLength();

        // Calculate the double-precision fraction of this number; as if the
        // binary point was left of the most significant '1' bit.
        // (Get the most significant 53 bits and divide by 2^53)
        long mask = 1L << 52; // mantissa is 53 bits (including hidden bit)
        long mantissa = 0;
        int j = 0;
        for (int i = 1; i < 54; i++)
        {
            j = n - i;
            if (j < 0) break;

            if (val.testBit(j)) mantissa |= mask;
            mask >>>= 1;
        }
        // Round up if next bit is 1.
        if (j > 0 && val.testBit(j - 1)) mantissa++;

        double f = mantissa / (double)(1L << 52);

        // Add the logarithm to the number of bits, and subtract 1 because the
        // number of bits is always higher than necessary for a number
        // (ie. log2(val)<n for every val).
        return (n - 1 + Math.log(f) * 1.44269504088896340735992468100189213742664595415298D);
        // Magic number converts from base e to base 2 before adding. For other
        // bases, correct the result, NOT this number!
    }
}
