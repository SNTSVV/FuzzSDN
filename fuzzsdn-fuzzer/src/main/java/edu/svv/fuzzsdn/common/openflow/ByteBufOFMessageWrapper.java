package edu.svv.fuzzsdn.common.openflow;

import com.google.common.hash.PrimitiveSink;
import edu.svv.fuzzsdn.common.exceptions.NotImplementedException;
import edu.svv.fuzzsdn.common.utils.Utils;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import org.projectfloodlight.openflow.protocol.OFMessage;
import org.projectfloodlight.openflow.protocol.OFType;
import org.projectfloodlight.openflow.protocol.OFVersion;


/**
 * ByteBufOFMessageWrapper is a wrapper around a {@link ByteBuf} and an {@link OFMessage}.
 * It allows to still use mechanics of an OFMessage while settings changing the payload of an OFMessage in a way that
 * would break the typical format of an OFMessage.
 */
public class ByteBufOFMessageWrapper implements OFMessage
{

    private ByteBuf mBuffer;

    // ====== ( Constructors ) =========================================================================================

    public ByteBufOFMessageWrapper(ByteBuf buffer)
    {
        this.mBuffer = buffer;
        this.mBuffer.retain(); // Retain the buffer so it is not discarded when another the creator is deleted;
        this.mBuffer.readerIndex();
    }

    public ByteBufOFMessageWrapper(OFMessage message)
    {
        this.mBuffer = Unpooled.buffer();
        message.writeTo(this.mBuffer);
    }

    // ====== ( Getters ) ==============================================================================================


    @Override
    public OFVersion getVersion()
    {
        // Start from the beginning
        mBuffer.readerIndex(0);

        // Read version
        int ofVersion = ((int) mBuffer.readByte() & 0xFF);

        for (OFVersion v : OFVersion.values())
        {
            if (ofVersion == v.getWireVersion())
                return v;
        }

        return null;
    }

    @Override
    public OFType getType()
    {
        // Start from the beginning
        mBuffer.readerIndex(0);
        mBuffer.skipBytes(1); // Skip Version
        byte type = mBuffer.readByte();

        for (OFType t : OFType.values())
        {
            if (type == t.ordinal())
                return t;
        }

        return null;
    }

    public short getLength()
    {
        // Start from the beginning
        mBuffer.readerIndex(0);

        mBuffer.skipBytes(1); // Skip Version
        mBuffer.skipBytes(1); // Skip Type

        return mBuffer.readShort(); // length
    }

    @Override
    public long getXid()
    {
        // Start from the beginning
        mBuffer.readerIndex(0);

        mBuffer.skipBytes(1); // Skip Version
        mBuffer.skipBytes(1); // skip type
        mBuffer.skipBytes(2); // skip length

        return mBuffer.readInt();
    }


    public byte[] getPayload()
    {
        // Start from the beginning
        mBuffer.readerIndex(0);
        int length = mBuffer.readableBytes();

        mBuffer.skipBytes(1);   // Skip Version
        mBuffer.skipBytes(1);   // Skip type
        mBuffer.skipBytes(2);   // Skip length
        mBuffer.skipBytes(4);   // Skip XID

        byte[] bytes = new byte[length - mBuffer.readerIndex()];
        mBuffer.readBytes(bytes);

        return bytes;
    }

    @Override
    public boolean equalsIgnoreXid(Object obj)
    {
        throw new NotImplementedException("Function \"equalsIgnoreXid\" is not yet implemented");
    }

    @Override
    public int hashCodeIgnoreXid()
    {
        throw new NotImplementedException("Function \"hashCodeIgnoreXid\" is not yet implemented");
    }

    @Override
    public void writeTo(ByteBuf channelBuffer)
    {
        // Start from the beginning
        mBuffer.readerIndex(0);

        byte[] bytes;
        int offset;
        int length = mBuffer.readableBytes();

        if (mBuffer.hasArray())
        {
            bytes = mBuffer.array();
            offset = mBuffer.arrayOffset();
        }
        else
        {
            bytes = new byte[length];
            mBuffer.getBytes(mBuffer.readerIndex(), bytes);
            offset = 0;
        }

        // Set the offset to the good position
        mBuffer.readerIndex(offset);

        // Write bytes to the buffer
        channelBuffer.writeBytes(bytes);
    }

    @Override
    public Builder createBuilder()
    {
        throw new NotImplementedException("No builder yet implemented for \""
                + this.getClass().getSimpleName()
                + "\" is not yet implemented");
    }


    @Override
    @SuppressWarnings("UnstableApiUsage")
    public void putTo(PrimitiveSink sink)
    {
        throw new NotImplementedException("Function \"putTo\" is not yet implemented");
    }

    @Override
    public String toString()
    {
        String s;
        if (this.getType() == OFType.PACKET_IN)
        {
            ByteBuf buf = Unpooled.buffer();
            buf.writeBytes(this.getPayload());
            buf.readerIndex(0);

            StringBuilder sb = new StringBuilder();

            int bufferId = buf.readInt();
            short totalLen = buf.readShort();
            byte reason = buf.readByte();
            byte tableId = buf.readByte();
            long cookie = buf.readLong();

            byte[] leftover = new byte[buf.readableBytes() - buf.readerIndex()];
            buf.readBytes(leftover);


            sb.append("OFPacketInMessage(");
            sb.append("xid=").append(this.getXid()).append(", ");
            sb.append("bufferId=").append(bufferId).append(", ");
            sb.append("totalLen=").append(totalLen).append(", ");
            sb.append("reason=");
            if (reason == 0)
                sb.append(reason).append("(NoMatch)");
            else if (reason == 1)
                sb.append(reason).append("(Action)");
            else if (reason == 3)
                sb.append(reason).append("(InvalidTTL)");
            else
                sb.append(reason);
            sb.append(", ");

            sb.append("tableId=").append(tableId).append(", ");
            sb.append("cookie=").append(cookie).append(", ");
            sb.append("data=[").append(Utils.bytesToHex(leftover)).append("])");

            s = sb.toString();
        }
        else
        {
            s = "OFMessage("
                + "version=" + this.getVersion() + ", "
                + "type=" + this.getType() + ", "
                + "xid=" + this.getXid() + ", "
                + "payload=\"" + Utils.bytesToHex(this.getPayload())
                + "\")";

        }

        return s;
    }
}
