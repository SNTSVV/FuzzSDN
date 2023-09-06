package edu.svv.fuzzsdn.fuzzer;

import edu.svv.fuzzsdn.fuzzer.instructions.actions.Action;
import edu.svv.fuzzsdn.common.openflow.PktStruct;
import edu.svv.fuzzsdn.fuzzer.configuration.AppPaths;
import edu.svv.fuzzsdn.common.utils.ByteBufUtil;
import io.netty.buffer.ByteBuf;
import org.apache.commons.codec.binary.Base64;
import org.jetbrains.annotations.NotNull;

import javax.json.Json;
import javax.json.JsonArrayBuilder;
import javax.json.JsonObject;
import javax.json.JsonObjectBuilder;
import java.io.FileWriter;
import java.io.IOException;
import java.math.BigInteger;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * This class store information about a fuzzing operation and has the capability to output a JSON-formatted report of
 * the operation
 */
public class Report
{
    // ===== ( Members ) ===============================================================================================

    // Timestamps
    private final long  start;
    private long        end;

    // Packets
    private byte[]      initialPacket;
    private byte[]      finalPacket;
    private PktStruct   pktStruct;

    // Mutations
    private final LinkedHashMap<Action, ArrayList<Mutation>> mutations;
    private Map.Entry<Action, ArrayList<Mutation>> currentAction = null;

    // Misc
    private FileWriter file;

    // ===== ( Constructors ) ==========================================================================================

    /**
     * Default constructor
     */
    public Report()
    {
        this.start = Instant.now().toEpochMilli();
        this.mutations = new LinkedHashMap<>();
    }


    /**
     * Copy constructor
     */
    public Report(@NotNull Report other)
    {
        this.start  = other.start;
        this.end    = other.end;
        // Packets
        if (other.initialPacket != null)
            this.initialPacket  = Arrays.copyOf(other.initialPacket, other.initialPacket.length);
        if (other.finalPacket != null)
            this.finalPacket    = Arrays.copyOf(other.finalPacket  , other.finalPacket.length);
        this.pktStruct      = new PktStruct().add(other.pktStruct, false);
        // Mutations
        this.mutations      = new LinkedHashMap<>();
        for (Map.Entry<Action, ArrayList<Mutation>> entry : other.mutations.entrySet())
        {
            // FIXME: Perform a copy as with this method the entries are copied by reference...
            this.mutations.put(entry.getKey(), entry.getValue());
        }
        // Dont copy the file writer or the current action
        this.currentAction  = null;
        this.file = null;
    }

    // ===== ( Getters ) ===============================================================================================

    public long getStart()
    {
        return this.start;
    }

    public long getEnd()
    {
        return this.end;
    }

    public byte[] getInitialPacket()
    {
        return initialPacket;
    }

    public byte[] getFinalPacket()
    {
        return finalPacket;
    }

    public Map<Action, ArrayList<Mutation>> getMutations()
    {
        return mutations;
    }

    public PktStruct getPktStruct()
    {
        return pktStruct;
    }

    // ===== ( Setters ) ===============================================================================================

    /**
     * Sets the packet structure
     */
    public Report setEnd()
    {
        this.end = Instant.now().toEpochMilli();
        this.writeToFile();
        return this;
    }

    /**
     * Sets the packet structure
     *
     * @param pktStruct The {@link PktStruct} to infer the structure from.
     * @return          This {@code Report} object
     */
    public Report setPktStruct(PktStruct pktStruct)
    {
        this.pktStruct = pktStruct;
        return this;
    }

    public Report setInitialPacket(ByteBuf msgBuf)
    {
        if (msgBuf == null)
            this.initialPacket = null;
        else
            this.initialPacket = ByteBufUtil.readAllBytes(msgBuf, true, true);

        return this;
    }

    /**
     * Sets the packet results after fuzzing {@link Action}
     *
     * @param msgBuf    The {@link ByteBuf} holding the final packet.
     * @see             Report#setFinalPacket(byte[])
     * @return          This {@code Report} object®
     */
    public Report setFinalPacket(ByteBuf msgBuf)
    {
        this.finalPacket = ByteBufUtil.readAllBytes(msgBuf, true, true);
        return this;
    }

    /**
     * Sets the packet results after fuzzing {@link Action}
     *
     * @see Report#setFinalPacket(ByteBuf)
     * @return      This {@code Report} object
     */
    public Report setFinalPacket(byte[] msgByteArray)
    {
        this.finalPacket = Arrays.copyOf(msgByteArray, msgByteArray.length);
        return this;
    }


    /**
     * Sets the current fuzzing {@link Action}
     *
     * @param action current action that is being performed
     * @return this {@code Report} object
     */
    public Report setCurrentAction(Action action)
    {
        // Add an entry to the mutations array
        ArrayList<Mutation> mutationList = new ArrayList<>();
        this.mutations.put(action, mutationList);

        // save the last entry
        for (Map.Entry<Action, ArrayList<Mutation>> actionArrayListEntry : this.mutations.entrySet())
        {
            currentAction = actionArrayListEntry;
        }

        return this;
    }

    /**
     * Register a  in the current report
     *
     * @param type          the {@link MutationType} of the mutation
     * @param field         the {@link String} representation of the field
     * @param initialValue  the {@link BigInteger} initial value the fuzzed field
     * @param finalValue    the {@link BigInteger} final value of the fuzzed the field
     *
     * @see Report#addMutation(Mutation)
     * @return this {@code Report} object
     */
    public Report addMutation(MutationType type, String field, BigInteger initialValue, BigInteger finalValue)
    {
        Mutation mutation = new Mutation();
        mutation.mutationType = type;
        mutation.field = field;
        mutation.initialValue = initialValue;
        mutation.finalValue = finalValue;

        // Add the mutation to the current action
        return this.addMutation(mutation);
    }

    /**
     * Register a {@link Mutation} in the current report
     *
     * @param mutation the mutation to be added
     * @return this {@code Report} object
     */
    public Report addMutation(Mutation mutation)
    {
        // Add the mutation to the current action
        currentAction.getValue().add(mutation);
        return this;
    }

    /**
     * Create the JSON representation of the report.
     *
     * @return the corresponding {@link JsonObject}
     */
    public JsonObject toJSON()
    {
        JsonObjectBuilder jObjBuilder = Json.createObjectBuilder();

        jObjBuilder.add("startTime"     , this.start);
        jObjBuilder.add("endTime"       , this.end);
        jObjBuilder.add("packetStruct"  , this.pktStruct.toJSON());
        jObjBuilder.add("initialPacket" , Base64.encodeBase64String(this.initialPacket));
        jObjBuilder.add("finalPacket"   , Base64.encodeBase64String(this.finalPacket));

        JsonArrayBuilder fuzzOps = Json.createArrayBuilder();
        for (Map.Entry<Action, ArrayList<Mutation>> fuzzAction : this.mutations.entrySet())
        {
            // Create operation jObj builder
            JsonObjectBuilder operation = Json.createObjectBuilder();

            // Add the action
            operation.add("action", fuzzAction.getKey().toJSON());

            // Add the mutations
            JsonArrayBuilder mutationJArr = Json.createArrayBuilder();
            for (Mutation mutation : fuzzAction.getValue())
            {
                mutationJArr.add(
                        Json.createObjectBuilder()
                                .add("type", mutation.mutationType.name())
                                .add("field", mutation.field)
                                .add("initialValue", mutation.initialValue)
                                .add("finalValue", mutation.finalValue)
                );
            }
            operation.add("mutations", mutationJArr);

            // Add the operation object to the json object
            fuzzOps.add(operation);
        }
        jObjBuilder.add("fuzzActions", fuzzOps);

        return jObjBuilder.build();
    }

    /**
     * Write the report to a file.
     *
     * @return          The corresponding {@link JsonObject}
     */
    public boolean writeToFile()
    {
        boolean success = false;
        String fileName = AppPaths.userDataDir().resolve("fuzz_report.json").toAbsolutePath().toString();

        try
        {
            // Constructs a FileWriter given a file name, using the platform's default charset
            file = new FileWriter(fileName);
            file.write(this.toJSON().toString());
            success = true;
        }
        catch (IOException e)
        {
            e.printStackTrace();
        }
        finally
        {
            try
            {
                file.flush();
                file.close();
            }
            catch (IOException e)
            {
                // TODO Auto-generated catch block
                e.printStackTrace();
            }
        }
        return success;
    }

    // ===== ( Object Overrides ) ======================================================================================

    @Override
    public String toString()
    {
        return toJSON().toString();
    }

    // ===== ( Mutation sub-class and enums) ===========================================================================

    /**
     * Categories of Mutations.
     */
    public enum MutationType
    {
        RULE_BASED_MUTATION,
        UNIFORM_MUTATION,
        RANDOM_MUTATION
    }

    /**
     * A struct like class to hold information about a mutation.
     */
    public static class Mutation
    {
        public MutationType mutationType;
        public String field;
        public BigInteger initialValue;
        public BigInteger finalValue;
    }

}
