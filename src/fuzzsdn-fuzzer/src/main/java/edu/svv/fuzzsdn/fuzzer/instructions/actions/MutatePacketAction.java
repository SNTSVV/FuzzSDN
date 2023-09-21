package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.fuzzer.Methods;
import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.projectfloodlight.openflow.protocol.OFMessage;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonObjectBuilder;
import java.util.Objects;

/**
 * Action which instruct the fuzzer to mutate a packet randomly.
 * See {@link Methods#mutatePacket } for implementation details
 */
public class MutatePacketAction extends Action
{
    private final boolean   includeHeader;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Constructor used by the builder
     * @param b Builder
     */
    protected MutatePacketAction(Builder b)
    {
        super(b);
        this.includeHeader  = b.includeHeader;
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Tells if the action should include the header
     * @return {@code true} if the header of the message must be included {@code false} otherwise.
     */
    public boolean includesHeader()
    {
        return this.includeHeader;
    }

    // ===== ( Public Methods ) ========================================================================================

    /**
     * Applicable to any OpenFlow message.
     * @see Action#canBeAppliedTo
     */
    @Override
    public boolean canBeAppliedTo(OFMessage msg)
    {
        return true;
    }

    /**
     * @see Action#toJSON()
     */
    @Override
    public JsonObject toJSON()
    {
        //
        JsonObjectBuilder jObjBuilder = Json.createObjectBuilder(super.toJSON());
        jObjBuilder.add("includeHeader", this.includeHeader);

        return jObjBuilder.build();
    }
    // ===== ( Object Overrides ) ======================================================================================

    /**
     * @see Action#toString
     */
    @Override
    public String toString()
    {
        return this.getClass().getSimpleName() + "(" +
                "intent=" + this.intent.name + "\", " +
                "target=" + this.target.name + "\", " +
                "header=" + this.includeHeader + ")";
    }

    /**
     * @see Action#hashCode
     */
    @Override
    public int hashCode()
    {
        return Objects.hash(this.intent, this.target, this.includeHeader);
    }

    // ===== ( Reader Class ) =========================================================================================

    /**
     * Reader for MutatePacket Action
     */
    public final static Reader READER = new Reader();
    public final static class Reader implements Action.Reader<MutatePacketAction>
    {
        // Action structure
        // {
        //      intent: "MUTATE_PACKET",
        //      includeHeader: boolean
        //      all: boolean
        //      random<ignored if all is true>: boolean
        //      fieldToMutateCount<ignored if all is true>: int
        // }

        /**
         * See {@link Action.Reader#readJSON}
         */
        @Nullable
        @Override
        public MutatePacketAction readJSON(@NotNull JsonObject jsonObject) throws ParsingException
        {
            // Check if all the mandatory keys are present
            // TODO: Check for all the mandatory keys and optional keys

            // Check if the intent is correct
            String intent = jsonObject.getString("intent");
            if (!intent.equalsIgnoreCase("MUTATE_PACKET"))
                throw new ParsingException("Wrong intent for MutatePacketAction (got: \"" + intent + "\", expected: \"MUTATE_PACKET\")");

            // Create the MutatePacketAction builder
            Builder builder = new Builder();

            // Check for includeHeader key
            if (jsonObject.containsKey("includeHeader"))
            {
                builder.includeHeader(jsonObject.getBoolean("includeHeader"));
            }
            else  // Default value to false
            {
                builder.includeHeader(false);
            }

            return builder.build();
        }
    }

    // ===== ( Builder ) ===============================================================================================

    /**
     * Builder for MutatePacket Action
     */
    public static class Builder extends Action.Builder<MutatePacketAction>
    {
        private boolean includeHeader;

        public Builder()
        {
            // Construct previous builder
            super();
            this.intent(Intent.MUTATE_PACKET).target(Target.OF_PACKET);

            // Default Values
            this.includeHeader = false;
        }

        public Builder includeHeader(boolean include)
        {
            this.includeHeader = include;
            return this;
        }

        public MutatePacketAction build()
        {
            return new MutatePacketAction(this);
        }
    }
}
