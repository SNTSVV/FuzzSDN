package edu.svv.fuzzsdn.common.utils;

import io.netty.buffer.ByteBuf;

import java.util.Arrays;


/**
 *
 */
public class ByteBufUtil
{
    /**
     * {@code keepIndexOffset} defaults to {@code true}.
     * @see ByteBufUtil#writeBytes(ByteBuf, byte[], int, boolean)
     */
    public static void writeBytes(ByteBuf buffer, byte[] bytes, int offset)
    {
        writeBytes(buffer, bytes, offset, true);
    }

    /**
     * Writes a byte array in a {@link ByteBuf} at the said offset
     * @param buffer the {@link ByteBuf} to writes the bytes from
     * @param bytes the {@code byte} array that old the bytes to read
     * @param offset the offset at which to start the writing
     * @param keepIndexOffset whether or not to keep the indexes as they were before writing
     */
    public static void writeBytes(ByteBuf buffer, byte[] bytes, int offset, boolean keepIndexOffset)
    {
        // Save the location of the write and reader index
        int bufRdOff = buffer.readerIndex();
        int bufWrOff = buffer.writerIndex();


        buffer.readerIndex(0); // Reset the reader index to 0 in order to be able to write bytes
        buffer.writerIndex(offset); // Set the writer index to the byte field location

        // Checks that we can writes the required bytes
        if (bytes.length > buffer.writableBytes())
        {
            String throwString = String.format("length(%d) exceeds buffer.writableBytes(%d) where buffer is: %s", bytes.length, buffer.writableBytes(), buffer);
            buffer.readerIndex(bufRdOff); // Sets the reader index to the original position
            buffer.writerIndex(bufWrOff); // Sets the writer index to the original position
            throw new IndexOutOfBoundsException(throwString);
        }

        // Writes the bytes to the buffer
        buffer.writeBytes(bytes);   // Write the bytes required

        // reset reader index
        if (keepIndexOffset)
        {
            buffer.writerIndex(bufWrOff); // Sets the writer index to the original position
            buffer.readerIndex(bufRdOff); // Sets the reader index to the original position
        }
    }

    /**
     * Read a byte array in a {@link ByteBuf} at the said offset
     */
    public static byte[] readAllBytes(ByteBuf buffer, boolean keepIndexOffset, boolean onlyReadable)
    {
        byte[] bytes;

        // Save the offset of the reader index
        int bufRdOff = buffer.readerIndex();
        int length = buffer.readableBytes();
        buffer.readerIndex(0);  // Reset the reader index

        if (buffer.hasArray())
        {
            // Clone the array to avoid passing a reference
            bytes = buffer.array().clone();
        }
        else
        {
            bytes = new byte[length];
            buffer.getBytes(buffer.readerIndex(), bytes);
        }

        if (keepIndexOffset)
        {
            buffer.readerIndex(bufRdOff); // Sets the reader index to the original position
        }

        if (onlyReadable)
        {
            bytes = Arrays.copyOf(bytes, buffer.readableBytes());
        }

        return bytes;
    }

    public static byte[] readAllBytes(ByteBuf buffer, boolean keepIndexOffset)
    {
        return readAllBytes(buffer, keepIndexOffset, false);
    }


    /**
     * Read a byte array in a {@link ByteBuf} at the said offset
     */
    public static byte[] readBytes(ByteBuf buffer, int offset, int length, boolean keepIndexOffset)
    {
        // Save the offset of the reader index
        int bufRdOff = buffer.readerIndex();

        // Create an array to store the bytes to read
        byte[] bytes = new byte[length];

        // Reset the reader index
        buffer.readerIndex(offset);

        // Get the bytes
        buffer.getBytes(buffer.readerIndex(), bytes); // Read the required bytes

        if (keepIndexOffset)
            buffer.readerIndex(bufRdOff); // Sets the reader index to the original position

        return bytes;
    }
}
