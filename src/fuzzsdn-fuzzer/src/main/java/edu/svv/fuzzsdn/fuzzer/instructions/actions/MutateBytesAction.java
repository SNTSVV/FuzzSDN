package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.projectfloodlight.openflow.protocol.OFMessage;

import javax.json.JsonObject;
import java.util.Objects;

public class MutateBytesAction extends Action
{

    private final boolean   includeHeader;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Constructor used by the builder
     * @param b Builder
     */
    protected MutateBytesAction(Builder b)
    {
        super(b);
        this.includeHeader = b.includeHeader;
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Tells if the action should include the header
     * @return {@code true} if the header of the message must be included {@code false} otherwise.
     */
    public boolean isHeaderIncluded()
    {
        return this.includeHeader;
    }


    // ===== ( Public Methods ) ========================================================================================

    /**
     * Applicable to any OpenFlow message.
     * See {@link Action#canBeAppliedTo} for more details
     */
    @Override
    public boolean canBeAppliedTo(OFMessage msg)
    {
        return true;
    }


    // ===== ( Object Overrides ) ======================================================================================

    /**
     * See {@link Action#toString} for more details
     */
    @Override
    public String toString()
    {
        return this.getClass().getSimpleName() +
                "(" +
                "intent=" + this.intent.name + ", " +
                "target=" + this.target.name + ", " +
                "includeHeader=" + this.includeHeader +
                ")";
    }

    /**
     * See {@link Action#hashCode} for more details
     */
    @Override
    public int hashCode()
    {
        return Objects.hash(this.intent, this.includeHeader);
    }

    // ===== ( Reader Class ) ==========================================================================================

    /**
     * Reader for MutatePacket Action
     */
    public final static Reader READER = new Reader();
    public final static class Reader implements Action.Reader<MutateBytesAction>
    {
        // Action structure
        // {
        //      "intent": "MUTATE_BYTE",
        //      "fieldName": <String>
        //      fieldToMutateCount<ignored if all is true>: int
        // }

        /**
         * See {@link Action.Reader#readJSON}
         */
        @Nullable
        @Override
        public MutateBytesAction readJSON(@NotNull JsonObject jObj) throws ParsingException
        {
            // Check if the intent is correct
            String intent = jObj.getString("intent");

            if (!intent.equalsIgnoreCase("mutate_bytes"))
                throw new ParsingException("Wrong intent for MutateBytesAction (got: \"" + intent + "\", expected: \"mutate_bytes\")");

            // Create the MutatePacketAction builder
            MutateBytesAction.Builder builder = new MutateBytesAction.Builder();

            // Check for includeHeader key
            if (jObj.containsKey("includeHeader"))
            {
                builder.includeHeader(jObj.getBoolean("includeHeader"));
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
    public static class Builder extends Action.Builder<MutateBytesAction>
    {
        private Boolean includeHeader;

        public Builder()
        {
            // Construct previous builder
            super();
            this.intent(Intent.MUTATE_BYTES).target(Target.OF_PACKET);
            // Default Values
            this.includeHeader = false;
        }

        public Builder includeHeader(boolean include)
        {
            this.includeHeader = include;
            return this;
        }

        public MutateBytesAction build()
        {
            return new MutateBytesAction(this);
        }
    }
}

