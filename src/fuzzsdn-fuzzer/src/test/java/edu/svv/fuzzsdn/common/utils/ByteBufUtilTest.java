package edu.svv.fuzzsdn.common.utils;

import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;

import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;

class ByteBufUtilTest
{

    // ===== ( writeBytes tests) =======================================================================================

    @RepeatedTest(50)
    void writeBytes_ShouldReadCorrectBytes_WhenInvokedCorrectly()
    {
        // Create a random byte buffer and a random sequence of bytes to read
        int length = 0;
        int lengthToWrite = 0;
        try
        {
            length = 50 + SecureRandom.getInstanceStrong().nextInt(9950);
            lengthToWrite = 1 + SecureRandom.getInstanceStrong().nextInt(length - 1);
        }
        catch (NoSuchAlgorithmException ignored){}

        byte[] bytes = new byte[length];
        byte[] bytesToWrite = new byte[lengthToWrite];
        int offset = 0;
        try
        {
            SecureRandom.getInstanceStrong().nextBytes(bytes);
            SecureRandom.getInstanceStrong().nextBytes(bytesToWrite);
            offset = SecureRandom.getInstanceStrong().nextInt(length - bytesToWrite.length);
        }
        catch (NoSuchAlgorithmException ignored){}

        // Copy original bytes into buffer
        ByteBuf buffer = Unpooled.copiedBuffer(bytes);

        // Write the bytes
        ByteBufUtil.writeBytes(buffer, bytesToWrite, offset);

        byte read;
        for (int i=0; i < length ; i++)
        {
            read = buffer.readByte();

            if (i >= offset && i < offset + bytesToWrite.length)
                Assertions.assertEquals(bytesToWrite[i - offset], read);
            else
                Assertions.assertEquals(bytes[i], read);
        }
    }

    @Test
    void writeBytes_ShouldThrowOutOfBoundException_WhenWritingMoreBytesThanBufferMaxCapacity()
    {
        // Declare an empty buffer
        ByteBuf buffer = Unpooled.EMPTY_BUFFER;
        // Declare some bytes that are more than 0
        byte[] bytesToWrite = {1, 2, 3, 4, 5, 6, 7};

        // Assert a IndexOutOfBoundsException is thrown
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> ByteBufUtil.writeBytes(buffer, bytesToWrite, 0));
    }

    // ===== ( readBytes tests) ========================================================================================

}