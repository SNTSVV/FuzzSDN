package edu.svv.fuzzsdn.common.utils;

import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;

import java.math.BigInteger;

class ByteUtilTest
{
    @RepeatedTest(10)
    void random_ShouldBeWithinBound_WhenMinAndMaxAreCorrectlyDefined()
    {
        BigInteger min = new BigInteger("999999999999999999999999999999999999999999999999995");
        BigInteger max = new BigInteger("999999999999999999999999999999999999999999999999999");

        BigInteger result = ByteUtil.randomBigInteger(min, max);

        Assertions.assertTrue(result.compareTo(min) >= 0);
        Assertions.assertTrue(result.compareTo(max) <= 0);
    }

    @Test
    void random_ShouldReturnMin_WhenMinAndMaxAreEqual()
    {
        BigInteger min = new BigInteger("100");
        BigInteger max = new BigInteger("100");

        BigInteger result = ByteUtil.randomBigInteger(min, max);

        Assertions.assertEquals(new BigInteger("100"), result);
    }

    @Test
    void log2_ShouldReturnCorrectValue()
    {
        final double threshold = 0.0000001;

        Assertions.assertTrue(Math.abs(0.0           -  ByteUtil.log2(BigInteger.ONE))                                          <= threshold);
        Assertions.assertTrue(Math.abs(1.0           -  ByteUtil.log2(BigInteger.TWO))                                          <= threshold);
        Assertions.assertTrue(Math.abs(3.32192809489 -  ByteUtil.log2(BigInteger.TEN))                                          <= threshold);
        Assertions.assertTrue(Math.abs(10.2691266791 -  ByteUtil.log2(new BigInteger("1234")))                              <= threshold);
        Assertions.assertTrue(Math.abs(99.6578428466 -  ByteUtil.log2(new BigInteger("999999999999999999999999999999")))    <= threshold);
    }
}