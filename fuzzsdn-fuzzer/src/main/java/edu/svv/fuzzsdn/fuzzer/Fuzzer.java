package edu.svv.fuzzsdn.fuzzer;

import edu.svv.fuzzsdn.common.exceptions.NotImplementedException;
import edu.svv.fuzzsdn.common.network.tcpproxy.ProxyHandler;
import edu.svv.fuzzsdn.common.utils.ByteBufUtil;
import edu.svv.fuzzsdn.common.openflow.OFPktStruct;
import edu.svv.fuzzsdn.common.openflow.PktStruct;
import edu.svv.fuzzsdn.fuzzer.configuration.AppPaths;
import edu.svv.fuzzsdn.fuzzer.configuration.Configuration;
import edu.svv.fuzzsdn.fuzzer.instructions.InstructionSet;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.*;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import org.projectfloodlight.openflow.exceptions.OFParseError;
import org.projectfloodlight.openflow.protocol.OFFactories;
import org.projectfloodlight.openflow.protocol.OFMessage;
import org.projectfloodlight.openflow.protocol.OFMessageReader;
import org.projectfloodlight.openflow.protocol.OFVersion;
import org.projectfloodlight.openflow.types.U16;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.SocketException;
import java.util.Arrays;
import java.util.Collection;


public class Fuzzer implements ProxyHandler
{
    // ===== ( Members ) ===============================================================================================

    // Logger
    private static final Logger log = LoggerFactory.getLogger(Fuzzer.class);

    // Constants
    private static final int OF_HEADER_LENGTH = 8; // bytes

    // Members
    private final OFMessageReader<OFMessage>    mOfReader;
    private InstructionSet                      mInstructionSet;
    private OFVersion                           mOfVersion;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Default constructor for fuzzer
     */
    public Fuzzer()
    {
        log.info("Setting up {}", getClass().getSimpleName());
        // Get configuration instance
        Configuration config = Configuration.getInstance();

        // Set OFMessage Reader.
        log.info("Parsing Openflow version...");
        String[] ofVersion = config.get("OpenflowVersion").split("\\.");
        this.mOfVersion = OFVersion.OF_10; // Default version to be used

        if (ofVersion.length >= 2)
        {
            if (ofVersion[0].equals("1"))
            {
                switch (Integer.parseInt(ofVersion[1]))
                {
                    case 0x05:
                        this.mOfVersion = OFVersion.OF_15;
                        break;
                    case 0x04:
                        this.mOfVersion = OFVersion.OF_14;
                        break;
                    case 0x03:
                        this.mOfVersion = OFVersion.OF_13;
                        break;
                    case 0x02:
                        this.mOfVersion = OFVersion.OF_12;
                        break;
                    case 0x01:
                        this.mOfVersion = OFVersion.OF_11;
                        break;
                    default:
                        log.warn("Openflow version \"{}.{}\" is not supported. Setting Openflow version to 1.0", ofVersion[0], ofVersion[1]);
                }
            }
            else
            {
                log.warn("Openflow version \"{}.{}\" is not supported. Setting Openflow version to 1.0", ofVersion[0], ofVersion[1]);
            }
        }
        else
        {
            log.warn("Openflow version \"{}\" is invalid. It should be of format \"MAJOR.MINOR(.REVISION)\".", config.get("OpenflowVersion"));
            log.warn("Setting Openflow version to 1.0");
        }

        // Set the initial fuzzer instructions
        // TODO: Handle the case where the instructions are passed via arguments
        //       If there is a default fuzzer instruction file, read it
        String path = AppPaths.userConfigDir().resolve("fuzzer_instr.json").toAbsolutePath().toString();
        File f = new File(path);
        if(f.exists() && !f.isDirectory())
        {
            log.info("User defined fuzzer instructions detected at \"{}\":", path);
        }
        // Otherwise, set the instruction from the default file
        else
        {
            path = AppPaths.userConfigDir().resolve("fuzzer_instr.json.default").toAbsolutePath().toString();
            log.info("Using default fuzzer instructions.");
        }
        this.setInstructionSetFromJSONFile(path);

        log.info("Using Openflow version \"{}\"", this.mOfVersion.toString());
        this.mOfReader = OFFactories.getFactory(this.mOfVersion).getReader();

    }

    // ===== ( Setters ) ===============================================================================================

    /**
     * Set the fuzzer instructions from a file
     *
     * @param path : path to the instructions file
     * @return this Fuzzer object
     */
    public Fuzzer setInstructionSetFromJSONFile(String path)
    {
        File f = new File(path);
        if(f.exists() && !f.isDirectory())  // Check if file exists
        {
            // Decode the instruction
            this.mInstructionSet = InstructionSet.READER.readJSONFile(path);

            if (this.mInstructionSet != null)
                log.info("Applying fuzzer instructions from \"{}\":\n\t{}", path, mInstructionSet);
            else
                log.error("Couldn't decode fuzzer instructions from \"{}\":", path);
        }
        else
        {
            log.error("No fuzzer instructions file under \"{}\"", path);
        }

        return this;
    }

    // ===== ( Private Methods ) =======================================================================================

    /**
     * This method fuzz an Openflow message passed as argument according
     * to predefined rules.
     *
     * @param msg OFMessage to fuzz
     * @return Fuzzed OFMessage
     */
    private ByteBuf fuzz(OFMessage msg)
    {
        // Default message to return is the one passed as argument
        ByteBuf msgBuf = Unpooled.buffer();
        msg.writeTo(msgBuf);

        // For each instruction
        Collection<Action> actionSet = mInstructionSet.getActionsFor(msg);
        // If there are actions to be applied on the packet
        if (actionSet != null)
        {
            // Initialize the fuzzing report
            Report report = new Report();

            if (log.isTraceEnabled())
            {
                byte[] bytes = ByteBufUtil.readAllBytes(msgBuf, true, true);
                log.trace("Original message: {}", Arrays.toString(bytes));
            }

            PktStruct pktStruct = OFPktStruct.fromOFMessage(msg); // Getting the message packet structure

            log.trace("Inferred PktStruct: " + pktStruct.toString());

            // Save original message to fuzzing report
            report
                    .setInitialPacket(msgBuf)
                    .setPktStruct(pktStruct);

            // for each actions
            for (Action action : actionSet)
            {
                log.debug("Handling action: " + action.toString());
                report.setCurrentAction(action);
                try
                {
                    switch(action.getIntent())
                    {
                        case MUTATE_PACKET:
                            Methods.mutatePacket(pktStruct, msgBuf, (MutatePacketAction) action, report);
                            break;

                        case MUTATE_PACKET_RULE:
                            Methods.mutatePacketRule(pktStruct, msgBuf, (MutatePacketRuleAction) action, report);
                            break;

                        case MUTATE_FIELD:
                            Methods.mutateField(pktStruct, msgBuf, (MutateFieldAction) action);
                            break;

                        case MUTATE_BYTES:
                            Methods.mutateBytes(pktStruct, msgBuf, (MutateBytesAction) action);
                            break;

                        default:
                            throw new NotImplementedException();
                    }
                }
                catch (Exception e)
                {
                    log.error("An Exception occurred during a fuzzing action:", e);
                }

            } // End of for(Action<?> action : actionSet)

            // Save the final message to fuzzing report
            report
                    .setFinalPacket(msgBuf)
                    .setEnd();

            if (log.isTraceEnabled())
            {
                byte[] bytes = ByteBufUtil.readAllBytes(msgBuf, true,true);
                log.trace("Fuzzed message: {}", Arrays.toString(bytes));
            }
        }
        else if (log.isTraceEnabled())
            log.trace("Forwarding OFMessage (version {} - XID {} - Type {})",
                    msg.getVersion().toString(),
                    msg.getXid(),
                    msg.getType().toString()
            );

        return msgBuf;

    }

    // ===== ( ProxyHandler Override and helper ) ======================================================================

    /**
     * See {@link ProxyHandler#onData}
     */
    @Override
    public void onData(InputStream in, OutputStream out)
    {
        byte[] readBytes = new byte[4096]; // Maximum amount of bytes to be read
        int readBytesLength;
        byte[] output = null;

        try
        {
            // Read inputStream
            while (-1 != (readBytesLength = in.read(readBytes)))
            {
                // Convert byte array into bytebuffer
                byte[] readBytesTrimmed = new byte[readBytesLength];
                System.arraycopy(readBytes, 0, readBytesTrimmed, 0, readBytesLength);
                ByteBuf bb_in = Unpooled.wrappedBuffer(readBytesTrimmed);

                try
                {
                    output = interpretAndFuzzData(bb_in);
                    // if there is a null output, just forward the data
                    if (output == null)
                        output = readBytesTrimmed;
                }
                catch (OFParseError e) // Handle error to not drop any data if there was an issue
                {
                    if (!e.getLocalizedMessage().equals("Message couldn't be read (null value)"))
                    {
                        log.error("An exception happened while parsing an Openflow Message:", e);
                        log.error("Forwarding the original data.");
                    }

                    output = readBytesTrimmed;
                }
                finally
                {
                    // If there was some data print to the output
                    if (output != null)
                    {
                        out.write(output, 0, output.length);
                        log.trace("Writing {} bytes to output stream", output.length);
                    }

                    // Clear bb_in buffer
                    bb_in.clear();

                    // Reset output
                    output = null;
                }
            }
        }
        catch (SocketException ignored) { }
        catch (IOException e)
        {
            log.error("Exception in {}@{}: {}", getClass().getSimpleName(), hashCode(), e.getMessage(), e);
        }
    }

    /**
     * Interprets the data read by the method {@link Fuzzer#onData} and fuzz them using the method {@link Fuzzer#fuzz}.
     *
     * @param bb data to be interpreted, encapsulated in a  {@link ByteBuf}.
     * @return a byte array of the data to be forwarded.
     *
     * @throws OFParseError when the data cannot be parsed into an Openflow message
     */
    private byte[] interpretAndFuzzData(ByteBuf bb) throws OFParseError
    {
        // Calculate length and initial offset
        int totalLen = bb.readableBytes();
        int offset = bb.readerIndex();

        // Prepare output byte
        byte[] output = new byte[totalLen];

        // Iterate through the ByteBuffer of the TCP Stream
        while (offset < totalLen)
        {
            // Read OFMessage version
            bb.readerIndex(offset);
            int version = ((int) bb.readByte() & 0xFF);

            // Read message length
            bb.readByte(); // skip type
            int length = U16.f(bb.readShort());

            // Return to the beginning of the byte Buffer
            bb.readerIndex(offset);

            // Check the version
            if (version != mOfVersion.getWireVersion())
            {
                // If the version is different, it might be a Segmented TCP Packet or anything else.
                // Return a null output
                log.debug("Message version is {} (!={}). Discarded.", version, mOfVersion.getWireVersion());
                return null;
            }

            // If the length less than a header length, then there was an error
            if (length < OF_HEADER_LENGTH)
                throw new OFParseError("Wrong length: Expected to be >= " + OF_HEADER_LENGTH + ", was: " + length);


            // Read the message
            OFMessage message = mOfReader.readFrom(bb);
            if (message != null)
            {
                // Write the message to a new byte buf
                ByteBuf bb_out;

                try
                {
                    bb_out = fuzz(message);
                }
                catch (Exception e)
                {
                    log.error(e.getMessage(), e);
                    bb_out = Unpooled.buffer();
                    message.writeTo(bb_out);
                }
                // Copy the fuzzed message to the output
                System.arraycopy(bb_out.array(), 0, output, offset, length);
            }
            else
            {
                // Throw an OFParseError because it was impossible to parse the data
                throw new OFParseError("Message couldn't be read (null value)");
            }

            // Add length to the offset
            offset += length;
        }

        return output;
    }
}
