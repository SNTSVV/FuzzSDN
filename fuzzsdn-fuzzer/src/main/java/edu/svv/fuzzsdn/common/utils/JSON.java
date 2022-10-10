package edu.svv.fuzzsdn.common.utils;

import edu.svv.fuzzsdn.common.exceptions.NotImplementedException;
import edu.svv.fuzzsdn.common.openflow.ByteBufOFMessageWrapper;
import edu.svv.fuzzsdn.common.utils.types.UInt16;
import edu.svv.fuzzsdn.common.utils.types.UInt32;
import edu.svv.fuzzsdn.common.utils.types.UInt8;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import org.projectfloodlight.openflow.protocol.OFMessage;
import org.projectfloodlight.openflow.protocol.OFPacketIn;
import org.projectfloodlight.openflow.protocol.OFType;
import org.projectfloodlight.openflow.types.U64;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.json.Json;
import javax.json.JsonBuilderFactory;
import javax.json.JsonObjectBuilder;
import java.math.BigInteger;
import java.util.Base64;

public class JSON
{

    private static final Logger log = LoggerFactory.getLogger(JSON.class);

    public static String OFMessageToJson(OFMessage msg)
    {
        String jsonString = null;

        // If it is a
        if (msg instanceof ByteBufOFMessageWrapper)
        {
            jsonString = ByteBufOFMessageWrapperToJSON((ByteBufOFMessageWrapper) msg);
        }
        else
        {
            if (msg.getType() == OFType.PACKET_IN)
                jsonString = OFPacketInToJson((OFPacketIn) msg);
        }

        return jsonString;
    }

    public static String OFPacketInToJson(OFPacketIn packetIn)
    {
        // TODO Implement support for other OFPacketIn
        throw new NotImplementedException("Utils.JSON#OfPacketInToJson is not yet implemented.");
    }

    public static String ByteBufOFMessageWrapperToJSON(ByteBufOFMessageWrapper msg)
    {

        JsonBuilderFactory factory = Json.createBuilderFactory(null);
        JsonObjectBuilder builder = factory.createObjectBuilder();


        if (msg.getType() == OFType.PACKET_IN)
        {
            ByteBuf buf = Unpooled.buffer();
            buf.writeBytes(msg.getPayload());
            buf.readerIndex(0);

            UInt32 bufferId     = new UInt32(buf.readInt());
            UInt16 totalLen     = new UInt16(buf.readShort());
            UInt8 reason        = new UInt8(buf.readByte());
            UInt8 tableId       = new UInt8(buf.readByte());
            BigInteger cookie   = U64.f(buf.readLong());

            // Read the matches
            int matchStart      = buf.readerIndex();
            UInt16 matchType    = new UInt16(buf.readShort());
            UInt16 matchLength  = new UInt16(buf.readShort());

            JsonObjectBuilder matchBuilder = factory.createObjectBuilder()
                    .add("type", matchType.getUnsigned())
                    .add("length", matchLength.getUnsigned());

            // read the match but limit it to the maximum length of the readableBytes
            byte[] matchBytes = new byte[Math.min(matchLength.getUnsigned(), buf.readableBytes())];
            buf.readBytes(matchBytes);
            matchBuilder.add("content", Base64.getEncoder().encodeToString(matchBytes));

            // align message to 8 bytes (length does not contain alignment)
            int toSkip = ((matchLength.getUnsigned() + 7)/8 * 8 ) - matchLength.getUnsigned();
            buf.skipBytes(Math.min(toSkip, buf.readableBytes()));

            byte[] data = new byte[buf.readableBytes()];
            buf.readBytes(data);

            builder.add("version"   , msg.getVersion().toString())
                    .add("type"     , msg.getType().toString())
                    .add("length"   , msg.getLength())
                    .add("xid"      , msg.getXid())
                    .add("buffer_id", bufferId.toString())
                    .add("total_len", totalLen.toString())
                    .add("reason"   , reason.toString())
                    .add("table_id" , tableId.toString())
                    .add("cookie"   , "0x" + cookie.toString())
                    .add("match"    , matchBuilder.build())
                    .add("data"     , Base64.getEncoder().encodeToString(data));
        }
        else
        {
            // TODO Implement support for other types
            throw new NotImplementedException("Utils.JSON#ByteBufOFMessageWrapperToJSON does not implement parsing for " + msg.getType());
        }

        // Return string representation
        return builder.build().toString();

    }
}
