package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.fuzzer.Methods;
import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import edu.svv.fuzzsdn.common.utils.types.Pair;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;
import org.projectfloodlight.openflow.protocol.OFMessage;

import javax.json.*;
import java.math.BigInteger;
import java.util.*;

/**
 * Action which instruct the fuzzer to mutate a packet while following a rule.
 * See {@link Methods#mutatePacketRule}  } for implementation details
 */
public class MutatePacketRuleAction extends Action
{
    private final boolean       includeHeader;
    private final int           ruleID;
    private final Set<Clause>   clauses;
    private final boolean       enableMutation;
    private final double        mutationRateMultiplier;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Constructor used by the builder
     * @param b Builder
     */
    protected MutatePacketRuleAction(Builder b)
    {
        super(b);
        this.ruleID                 = b.ruleID;
        this.includeHeader          = b.includeHeader;
        this.clauses                = b.clauses;
        this.enableMutation         = b.enableMutation;
        this.mutationRateMultiplier = b.mutationRateMultiplier;
    }

    // ===== ( Getters ) ===============================================================================================


    /**
     * Returns the {@code int} ID of the rule that is claused are made for
     * @return {@code int}
     */
    public int getRuleID()
    {
        return this.ruleID;
    }

    /**
     * Tells if the action should include the header
     * @return {@code true} if the header of the message must be included {@code false} otherwise.
     */
    public boolean isHeaderIncluded()
    {
        return this.includeHeader;
    }

    /**
     * Tells if a mutation of the packet is required by the action.
     * @return {@code true} if the mutation of the packet should be done, {@code false} otherwise.
     */
    public boolean isMutationEnabled()
    {
        return this.enableMutation;
    }

    /**
     * Returns the mutationRateMultiplier to be applied
     * @return a {@code double} corresponding to the mutationRateMultiplier
     */
    public double getMutationRateMultiplier()
    {
        return this.mutationRateMultiplier;
    }

    /**
     * Returns the list of {@link Clause} that are applied to the
     * @return a {@link Set} of {@link Clause}
     */
    public Set<Clause> getClauses()
    {
        return this.clauses;
    }

    /**
     * Returns the number of {@link Clause} that are applied to the
     * @return an {@code int}
     */
    public int conditionCount()
    {
        return this.clauses.size();
    }

    // ===== ( Public Methods ) ========================================================================================

    /**
     * Applicable to any OpenFlow message.
     * See {@link Action#canBeAppliedTo} for more details
     */
    public boolean canBeAppliedTo(OFMessage msg)
    {
        return true;
    }

    /**
     * @see Action#toJSON
     */
    @Override
    public JsonObject toJSON()
    {
        //
        JsonObjectBuilder jObjBuilder = Json.createObjectBuilder(super.toJSON());
        jObjBuilder.add("ruleID", this.ruleID);
        jObjBuilder.add("includeHeader", this.includeHeader);
        jObjBuilder.add("enableMutation", this.enableMutation);
        if (this.enableMutation)
            jObjBuilder.add("mutationRateMultiplier", this.mutationRateMultiplier);

        // Add information about the rules
        if (this.clauses.size() > 0)
        {
            JsonArrayBuilder clJArr = Json.createArrayBuilder();
            JsonObjectBuilder clJObj;

            for (Clause clause: this.clauses)
            {
                clJObj = Json.createObjectBuilder();
                clJObj.add("field", clause.getField());

                if (clause.isRanged())
                {
                    Collection<Pair<BigInteger>> range = clause.getRange();
                    if (range != null)
                    {
                        JsonArrayBuilder rangeArr = Json.createArrayBuilder();
                        for (Pair<BigInteger> r : range)
                        {
                            rangeArr.add(
                                    Json.createArrayBuilder()
                                            .add(r.left)
                                            .add(r.right)
                            );
                        }
                        clJObj.add("range", rangeArr);
                    }
                }
                else if (!clause.isRanged())
                {
                    BigInteger value = clause.getValue();
                    if (value != null)
                    {
                        clJObj.add("value", value);
                    }
                }

                // Add the object to the array
                clJArr.add(clJObj);
            }

            // Add the clause array to the object
            jObjBuilder.add("clauses", clJArr);
        }

        return jObjBuilder.build();
    }

    // ===== ( Object Overrides ) ======================================================================================

    /**
     * See {@link Action#toString} for more details
     */
    @Override
    public String toString()
    {
        StringBuilder sb = new StringBuilder();
        sb.append(this.getClass().getSimpleName()).append("(");
        sb.append("intent=\"").append(this.intent.name).append("\", ");
        sb.append("target=\"").append(this.target.name).append("\", ");
        sb.append("ruleID=").append(this.ruleID).append(", ");
        sb.append("includeHeader=").append(this.includeHeader).append(", ");

        // Add information about mutation
        sb.append("enableMutation=").append(this.enableMutation);
        if (this.enableMutation)
            sb.append(", ").append("mutationRateMultiplier=").append(this.mutationRateMultiplier);

        // Add information about the rules
        if (this.clauses.size() > 0)
        {
            sb.append(", ").append("clauses=").append("[");
            boolean first = true;
            for (Clause clause: this.clauses)
            {
                if (first)
                    first = false;
                else
                    sb.append(", ");
                sb.append(clause);
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
        return Objects.hash(this.intent, this.target, this.includeHeader);
    }

    // ===== ( Reader Class ) ==========================================================================================

    /**
     * Reader for MutatePacket Action
     */
    public final static Reader READER = new Reader();
    public final static class Reader implements Action.Reader<MutatePacketRuleAction>
    {
        // Action structure
        // {
        //      intent: "MUTATE_PACKET",
        //      includeHeader: boolean
        //      rule: [
        //          {
        //              "value": integer, optional, shouldn't be used alongside a a range
        //              "enableMutation": boolean, optional, default to false
        //              "mutationRateMultiplier": double
        //              "rule": {
        //                  "ID": integer, identifies the rule
        //                  "clauses": [
        //                      {
        //                          "field": string, name of the field for the clause
        //                          "range": array of 2-member array, optional"
        //                          "value": value the clause should take
        //                      }
        //                  ],
        //              },
        //          },
        //      ]
        // }

        /**
         * See {@link Action.Reader#readJSON}
         */
        @Nullable
        @Override
        public MutatePacketRuleAction readJSON(@NotNull JsonObject jsonObject) throws ParsingException
        {
            // Check if all the mandatory keys are present
            // TODO: Check for all the mandatory keys and optional keys

            // Check if the intent is correct
            String intent = jsonObject.getString("intent");
            if (!intent.equalsIgnoreCase("MUTATE_PACKET_RULE"))
                throw new ParsingException("Wrong intent for MutatePacketRuleAction (got: \"" + intent + "\", expected: \"MUTATE_PACKET_RULE\")");

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

            // Check the enable mutation key
            if (jsonObject.containsKey("enableMutation"))
            {
                builder.enableMutation(jsonObject.getBoolean("enableMutation"));
            }
            else  // default value to false
            {
                builder.enableMutation(false);
            }

            // Check the mutation multiplier key
            if (jsonObject.containsKey("mutationRateMultiplier"))
            {
                builder.mutationRateMultiplier(jsonObject.getJsonNumber("mutationRateMultiplier").doubleValue());
            }


            // Parse the rule
            if (jsonObject.containsKey("rule"))
            {
                // Iterate through the condition
                JsonObject ruleObj = jsonObject.getJsonObject("rule");
                if (ruleObj.containsKey("id"))
                    builder.ruleID(ruleObj.getInt("id"));

                JsonArray clausesJArray = ruleObj.getJsonArray("clauses");
                for (int i = 0 ; i < clausesJArray.size() ; i++)
                {
                    // Get the clause object, field and ranges array
                    JsonObject cdtObj = clausesJArray.getJsonObject(i);
                    String field = cdtObj.getString("field");
                    // If a range is defined...
                    if (cdtObj.containsKey("range"))
                    {
                        JsonArray rangeArray = cdtObj.getJsonArray("range");

                        // Parse the range
                        Set<Pair<BigInteger>> range = new HashSet<>();
                        for (int j = 0 ; j < rangeArray.size() ; j++)
                        {
                            range.add(
                                    new Pair<>(
                                            rangeArray.getJsonArray(j).getJsonNumber(0).bigIntegerValue(),
                                            rangeArray.getJsonArray(j).getJsonNumber(1).bigIntegerValue()
                                    )
                            );
                        }
                        builder.addClause(field, range);
                    }
                    // if a value is defined...
                    else if (cdtObj.containsKey("value"))
                    {
                        BigInteger value = cdtObj.getJsonNumber("value").bigIntegerValue();
                        builder.addClause(field, value);
                    }
                }
            }

            return builder.build();
        }
    }

    // ===== ( Builder Class ) =========================================================================================

    /**
     * Builder for MutatePacketRule Action
     */
    public static class Builder extends Action.Builder<MutatePacketRuleAction>
    {
        private int                 ruleID;
        private boolean             includeHeader;
        private final Set<Clause>   clauses;
        private boolean             enableMutation;
        private double              mutationRateMultiplier;

        public Builder()
        {
            // Construct previous builder
            super();
            this.intent(Intent.MUTATE_PACKET_RULE).target(Target.OF_PACKET);

            // Initialization
            this.includeHeader          = false;
            this.clauses                = new HashSet<>();
            this.enableMutation         = false;
            this.mutationRateMultiplier = 1.0;
            this.ruleID                 = -1;
        }

        public Builder ruleID(int id)
        {
            this.ruleID = id;
            return this;
        }

        public Builder includeHeader(boolean include)
        {
            this.includeHeader = include;
            return this;
        }

        public Builder enableMutation(boolean enable)
        {
            this.enableMutation = enable;
            return this;
        }

        public Builder mutationRateMultiplier(double multiplier)
        {
            this.mutationRateMultiplier = multiplier;
            return this;
        }

        @SafeVarargs
        public final Builder addClause(String field, Pair<BigInteger>... range)
        {
            this.clauses.add(new Clause(field, range));
            return this;
        }

        public final Builder addClause(String field, Collection<Pair<BigInteger>> range)
        {
            this.clauses.add(new Clause(field, range));
            return this;
        }

        public final Builder addClause(String field, BigInteger value)
        {
            this.clauses.add(new Clause(field, value));
            return this;
        }

        public final Builder addClause(Clause cdt)
        {
            this.clauses.add(cdt);
            return this;
        }

        public MutatePacketRuleAction build()
        {
            return new MutatePacketRuleAction(this);
        }
    }


    // ===== ( Clause Inner Class ) =================================================================================

    public static class Clause
    {
        private final String                field;
        private final boolean               ranged;
        private final Set<Pair<BigInteger>> range;
        private final BigInteger            value;

        @SafeVarargs
        public Clause(String field, Pair<BigInteger>... range)
        {
            this.field = field;
            this.ranged = true;
            this.range = new HashSet<>();
            this.range.addAll(Arrays.asList(range));
            this.value = null;
        }

        public Clause(String field, Collection<Pair<BigInteger>> range)
        {
            this.field = field;
            this.ranged = true;
            this.range = new HashSet<>();
            this.range.addAll(range);
            this.value = null;
        }


        public Clause(String field, BigInteger value)
        {
            this.field = field;
            this.ranged = false;
            this.value = value;
            this.range = null;
        }

        public String getField()
        {
            return this.field;
        }

        public boolean isRanged()
        {
            return this.ranged;
        }

        public Collection<Pair<BigInteger>> getRange()
        {
            return this.range;
        }

        public BigInteger getValue()
        {
            return this.value;
        }

        @Override
        public String toString()
        {
            StringBuilder sb = new StringBuilder(this.getClass().getSimpleName()).append("(");

            sb.append("field=").append(this.field);

            if (this.ranged && this.range != null)
            {
                sb.append(", ").append("range=[");
                boolean first = true;
                for (Pair<BigInteger> r : this.range)
                {
                    if (first)
                        first = false;
                    else
                        sb.append(", ");
                    sb.append("(").append(r.right).append(", ").append(r.left).append(")");
                }
                sb.append("]");
            }
            else if (!this.ranged && this.value != null)
            {
                sb.append(", ").append("value=").append(this.value);
            }
            sb.append(")");

            return sb.toString();
        }
    }
}

