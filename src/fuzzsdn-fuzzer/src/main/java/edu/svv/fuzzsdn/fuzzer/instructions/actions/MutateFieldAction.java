package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import edu.svv.fuzzsdn.common.utils.types.Pair;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.projectfloodlight.openflow.protocol.OFMessage;

import javax.json.JsonArray;
import javax.json.JsonObject;
import javax.json.JsonValue;
import java.math.BigInteger;
import java.util.Collection;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

public class MutateFieldAction extends Action
{
    private final String                fieldName;
    private final Set<Pair<BigInteger>> ranges;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Constructor used by the builder
     * @param b Builder
     */
    protected MutateFieldAction(Builder b)
    {
        super(b);
        this.fieldName = b.fieldName;
        this.ranges = b.ranges;

        // Validate that the action is correctly formatted
        if (this.ranges != null)
            for (Pair<BigInteger> r : this.ranges)
                if (r.left.compareTo(r.right) > 0)
                {
                    throw new IllegalStateException("The max value of a range should be superior or equal to its minimum value "
                            + "(expected a value >= " + r.left
                            + ", got " + r.right + ")"
                            );
                }
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Get the name of the field to mutate
     * @return return the number of fields to mutate. return -1 if all fields are to be mutated
     */
    public String getFieldName()
    {
        return this.fieldName;
    }

    /**
     * Return the min value the fuzzed field can take.
     * @return the {@link BigInteger} max value of the field or {@code null} if there is no upper bound.
     */
    public Collection<Pair<BigInteger>> getRanges()
    {
        return this.ranges;
    }


    // ===== ( Public Methods ) ========================================================================================

    /**
     * Applicable to any OpenFlow message.
     * See {@link Action#canBeAppliedTo} for more details
     */
    // TODO: Verify if the field exists in the OFMessage
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
        StringBuilder sb = new StringBuilder(this.getClass().getSimpleName()).append("(");
        sb.append("intent=").append(this.intent.name);
        sb.append(", target=").append(this.target.name);
        sb.append(", fieldName=").append(this.fieldName);
        boolean first = true;
        if (this.ranges != null)
        {
            sb.append(", ranges=[");
            for (Pair<BigInteger> range : this.ranges)
            {
                if (first)
                    first = false;
                else
                    sb.append(", ");
                sb.append("(").append(range.left).append(", ").append(range.right).append(")");
            }
            sb.append("]");
        }
        sb.append(")");

        return sb.toString();
    }

    /**
     * See {@link Action#hashCode} for more details
     */
    @Override
    public int hashCode()
    {
        return Objects.hash(this.intent, this.target, this.fieldName, this.ranges);
    }

    // ===== ( Reader Class ) ==========================================================================================

    /**
     * Reader for MutatePacket Action
     */
    public final static Reader READER = new Reader();
    public final static class Reader implements Action.Reader<MutateFieldAction>
    {
        // Action structure
        // {
        //      "intent": "MUTATE_FIELD",
        //      "fieldName": <String>
        //      fieldToMutateCount<ignored if all is true>: int
        // }

        /**
         * See {@link Action.Reader#readJSON}
         */
        @Nullable
        @Override
        public MutateFieldAction readJSON(@NotNull JsonObject jObj) throws ParsingException
        {
            // Check if all the mandatory keys are present
            // TODO: Check for all the mandatory keys and optional keys

            // Check if the intent is correct
            String intent = jObj.getString("intent");
            if (!intent.equalsIgnoreCase("MUTATE_FIELD"))
                throw new ParsingException("Wrong intent for MutateFieldAction (got: \"" + intent + "\", expected: \"MUTATE_FIELD\")");

            // Create the MutatePacketAction builder
            Builder builder = new Builder();
            builder.fieldName(jObj.getString("fieldName"));

            if (jObj.containsKey("range"))
            {
                // Get the range
                JsonArray range_array = jObj.getJsonArray("range");
                BigInteger min;
                BigInteger max;

                for (JsonValue sub : range_array)
                {
                    min = sub.asJsonArray().getJsonNumber(0).bigIntegerValue();
                    max = sub.asJsonArray().getJsonNumber(1).bigIntegerValue();
                    builder.range(min, max);
                }
            }

            return builder.build();
        }
    }

    // ===== ( Builder ) ===============================================================================================

    /**
     * Builder for MutatePacket Action
     */
    public static class Builder extends Action.Builder<MutateFieldAction>
    {
        private String                  fieldName;
        private Set<Pair<BigInteger>>   ranges;

        public Builder()
        {
            // Construct previous builder
            super();
            this.intent(Intent.MUTATE_FIELD).target(Target.OF_PACKET);
            // Default Values
            this.fieldName = null;
            this.ranges = null;
        }

        public Builder fieldName(String name)
        {
            this.fieldName = name;
            return this;
        }

        // TODO: Separate method in a range and a subrange method
        public Builder range(BigInteger min, BigInteger max)
        {
            if (this.ranges == null)
                this.ranges = new HashSet<>();
            this.ranges.add(new Pair<>(min, max));
            return this;
        }

        public MutateFieldAction build()
        {
            return new MutateFieldAction(this);
        }
    }
}
