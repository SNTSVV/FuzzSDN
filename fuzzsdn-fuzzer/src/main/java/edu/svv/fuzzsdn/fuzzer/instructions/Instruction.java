package edu.svv.fuzzsdn.fuzzer.instructions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.*;
import edu.svv.fuzzsdn.fuzzer.instructions.criteria.*;
import org.pcap4j.packet.namednumber.EtherType;
import org.pcap4j.util.MacAddress;
import org.projectfloodlight.openflow.protocol.OFMessage;
import org.projectfloodlight.openflow.protocol.OFType;

import javax.json.JsonArray;
import javax.json.JsonObject;
import javax.json.JsonString;
import javax.json.JsonValue;
import java.util.*;

/**
 * An instruction to be executed by the fuzzer.
 * An Instruction holds an {@link HashSet} of {@link Criterion} and a HashSet of {@link Action}. For any given
 * message, if the complete set of criterion matches the packet, then the instruction dispatch which actions should
 * be taken by the fuzzer.
 */
public class Instruction
{

    // ===== ( Members ) ===============================================================================================

    private final Set<CriteriaSet>  mCriteria;
    private final Set<Action>       mActions;
    private final boolean           hasMatchLimit;
    private long                    matchCount;
    private final long              matchLimit;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Default constructor, needs a builder
     */
    private Instruction(Builder b)
    {
        this.mCriteria      = b.criteriaSets;
        this.mActions       = b.actions;
        this.hasMatchLimit  = b.enableMatchLimit;
        this.matchLimit     = b.matchLimit;
        this.matchCount     = 0;
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Get the collection of criteria stored in the instruction
     *
     * @return a {@link java.util.Collection} of {@link CriteriaSet}
     */
    public Collection<CriteriaSet> getCriteria()
    {
        return this.mCriteria;
    }

    /**
     * Get the collection of actions stored in the instruction
     *
     * @return a {@link java.util.Collection} of {@link Action}
     */
    public Collection<Action> getActions()
    {
        return this.mActions;
    }

    /**
     * Determine if an instruction has expired.
     *
     * @return true if the match has expired, false otherwise.
     */
    public boolean hasExpired()
    {
        if (hasMatchLimit && (matchLimit - matchCount) > 0 )
            return false;
        else
            return hasMatchLimit;
    }


    /**
     * Get the maximum number of match allowed for this Instruction
     *
     * @return the {@code long} representation of the match count. {@code 0} is returned if there is no match limit.
     */
    public long getMatchLimit()
    {
        if (this.hasMatchLimit)
            return this.matchLimit;
        else
            return 0;
    }

    /**
     * Get the number of match that occurred for this Instruction
     *
     * @return the {@code long} representation of the match count. {@code 0} is returned if there is no match limit.
     */
    public long getMatchCount()
    {
        if (this.hasMatchLimit)
            return this.matchCount;
        else
            return 0;
    }

    // ===== ( Methods ) ===============================================================================================

    /**
     * Determine if a OFMessage is matching all the criteria of the instruction.
     *
     * @param msg The OFMessage to check
     * @return true if the OFMessage is matching all the criteria, else return false
     */
    public boolean isMatching(OFMessage msg)
    {
        // If there is no criteria then everything works
        if (this.mCriteria.isEmpty())
            return true;

        // Otherwise...
        boolean matching = false;
        for (CriteriaSet criteria : mCriteria)
        {
            // If one of the criteria set is satisfied, then the actions can be applied
            if (criteria.isSatisfied(msg))
            {
                matching = true;
                break;  // Break out of the loop as one of the criterion is not matched
            }
        }

        // Increase the match count
        if (matching)
            ++this.matchCount;

        return matching;
    }

    // ===== ( Object Overrides ) ======================================================================================

    /**
     * See {@link Object#toString}
     */
    public String toString()
    {
        StringBuilder sb = new StringBuilder("Instruction(");
        boolean first;

        // Display Criteria
        first = true;
        sb.append("criteria=[");
        for (CriteriaSet criteria : mCriteria)
        {
            if (first)
                first = false;
            else
                sb.append(", ");
            sb.append(criteria.toString());
        }
        sb.append("], ");

        // Display Actions
        first = true;
        sb.append("actions=[");
        for (Action action : mActions)
        {
            if (first)
                first = false;
            else
                sb.append(", ");
            sb.append(action.toString());
        }
        sb.append("]");

        // Append match limit if applicable
        if (this.hasMatchLimit)
        {
            sb.append(", matchLimit=").append(this.matchLimit);
            sb.append(", matchCount=").append(this.matchCount);
        }

        sb.append(")");
        return sb.toString();
    }

    /**
     * see {@link Object#equals(Object)}
     */
    @Override
    public boolean equals(Object o)
    {
        boolean result;
        if (o == this)
            result = true;
        else if (!(o instanceof Instruction))
            result = false;
        else
        {
            Instruction other = (Instruction) o;
            result = Objects.equals(this.getCriteria(), other.getCriteria())
                    && Objects.equals(this.getActions(), other.getActions());

            // Match limit and match count are ignored on purpose, so the equality only depends on the
            // Actions and Criteria lists
        }

        return result;
    }

    /**
     * Override of {@link Object#hashCode} so the hashCode is the same when the collections of actions and criteria
     * are the same.
     */
    @Override
    public int hashCode()
    {
        return Objects.hash(this.getCriteria(), this.getActions());
    }

    // ===== ( Builder ) ===============================================================================================

    /**
     * Builder for Instruction Class Action
     */
    public final static class Builder
    {
        private Set<CriteriaSet>    criteriaSets;
        private Set<Action>         actions;
        private boolean             enableMatchLimit;
        private long                matchLimit;

        private boolean all;

        public Builder()
        {
            // Construct previous builder
            this.criteriaSets       = new HashSet<>();
            this.actions            = new HashSet<>();
            this.enableMatchLimit   = false;
            this.matchLimit         = 0;
        }

        /**
         * Add a set of criteria to the instruction.
         *
         * @param criteriaSets the {@link CriteriaSet} to be added to the instruction
         * @return this Builder object
         */
        public Builder criteriaSet(CriteriaSet... criteriaSets)
        {
            this.criteriaSets.addAll(Arrays.asList(criteriaSets));
            return this;
        }

        /**
         * Add a set of actions to the instruction.
         *
         * @param actions the {@link Action}s to be added to the instruction
         * @return this Builder object
         */
        public Builder actions(Action... actions)
        {
            this.actions.addAll(Arrays.asList(actions));
            return this;
        }

        public Builder matchLimit(boolean enable)
        {
            // Default value for limit is 1
            return matchLimit(enable, 1);
        }

        public Builder matchLimit(boolean enable, long limit)
        {
            if (enable)
            {
                if (limit <= 0)
                    throw new IllegalArgumentException("The match limit should be > 0 (got " + limit + ")");

                this.enableMatchLimit = true;
                this.matchLimit = limit;
            }
            else
            {
                this.enableMatchLimit = false;
                this.matchLimit = 0;
            }

            return this;
        }


        public Instruction build()
        {
            return new Instruction(this);
        }
    }

    // ===== ( Reader ) ================================================================================================

    public final static Reader READER = new Reader();
    public final static class Reader
    {
        // ===== (Private Methods) =========================================================================================

        //  {
        //      "matchLimit" <int>
        //      "criteria" <Array of Criteria objects>
        //      "actions": <Array of Actions>
        //  }
        /**
         * Process a JsonObject containing a set of instructions.
         *
         * @param jsonObject : the {@link JsonObject} containing the instructions.
         * @return an {@link InstructionSet} containing the parsed instructions. Returns null if no instructions are parsed
         */
        public static Instruction readJSON(JsonObject jsonObject) throws ParsingException
        {
            // Declare the builder
            Builder builder = new Builder();

            Collection<CriteriaSet> criteriaSetCollection;

            // First parse the criteria if they exist
            // TODO: Create a builder for criteria
            if (jsonObject.containsKey("criteria"))
            {
                criteriaSetCollection = parseCriteriaArray(jsonObject.getJsonArray("criteria"));
                for (CriteriaSet cs : criteriaSetCollection)
                    builder.criteriaSet(cs);
            }

            // Then parse the actions array if it exists
            if (jsonObject.containsKey("actions"))
            {
                JsonArray actionArray = jsonObject.getJsonArray("actions");
                JsonObject actionObj;

                for (JsonValue actionVal : actionArray)
                {
                    // Cast JsonValue to JsonObject
                    actionObj = (JsonObject) actionVal;
                    // Each criterion in the criteria array should be a JSON object that contains criteria

                    String intent = actionObj.getString("intent");

                    switch (Action.Intent.fromString(intent))
                    {
                        case MUTATE_BYTES:
                            builder.actions(MutateBytesAction.READER.readJSON(actionObj));
                            break;

                        case MUTATE_PACKET:
                            builder.actions(MutatePacketAction.READER.readJSON(actionObj));
                            break;

                        case MUTATE_PACKET_RULE:
                            builder.actions(MutatePacketRuleAction.READER.readJSON(actionObj));
                            break;

                        case MUTATE_FIELD:
                            builder.actions(MutateFieldAction.READER.readJSON(actionObj));
                            break;

                        default:
                            throw new ParsingException("Unknown Action for intent \"" + intent + "\"");
                    }
                }
            }

            // Finally add the match limit if it exists
            if (jsonObject.containsKey("matchLimit"))
                builder.matchLimit(true, jsonObject.getInt("matchLimit"));
            else
                builder.matchLimit(false);

            // Build the instruction
            return builder.build();
        }


        private static Set<CriteriaSet> parseCriteriaArray(JsonArray criteriaArray)
        {
            Set<CriteriaSet> criteriaSet = new HashSet<>();

            for (JsonValue criterion : criteriaArray)
            {
                // Each criterion in the criteria array should be a JSON object that contains criteria
                if (criterion.getValueType() == JsonValue.ValueType.OBJECT)
                {
                    criteriaSet.add(parseCriteriaObject((JsonObject) criterion));
                }
                else
                {
                    throw new IllegalArgumentException("");  // TODO: Make proper error message
                }
            }

            return criteriaSet;
        }


        private static CriteriaSet parseCriteriaObject(JsonObject criteriaObject)
        {
            Set<String> keys = criteriaObject.keySet();
            CriteriaSet criteria = new CriteriaSet();

            for (String key : keys)
            {
                JsonValue value = criteriaObject.get(key);
                JsonValue.ValueType type = value.getValueType();

                // TODO: Handle the case when we have arrays
                // TODO: throw errors when the parsing is not good

                Criterion<?> criterion  = null;
                switch (key)
                {

                    // Packet In / Packet Out Ethernet Src / Dst
                    case "ethSrc":
                    case "ethDst":
                        if (type == JsonValue.ValueType.STRING)
                        {
                            String valueString = ((JsonString) value).getString().toUpperCase();
                            MacAddress macAddress = MacAddress.getByName(valueString);

                            if (key.equals("ethSrc"))
                                criterion = new EthAddrCriterion(true, macAddress);
                            else
                                criterion = new EthAddrCriterion(false, macAddress);
                        }
                        criteria.addCriterion(criterion);
                        break;

                    // Packet In / Packet Out Ethernet Type
                    case "ethType":
                        if (type == JsonValue.ValueType.STRING)
                        {
                            String valueString = ((JsonString) value).getString().toUpperCase();
                            switch (valueString)
                            {
                                case "ARP":
                                    criterion = new EthTypeCriterion(EtherType.ARP);
                                    break;
                                case "IPV4":
                                    criterion = new EthTypeCriterion(EtherType.IPV4);
                                    break;
                                case "DOT1Q_VLAN_TAGGED_FRAMES":
                                    criterion = new EthTypeCriterion(EtherType.DOT1Q_VLAN_TAGGED_FRAMES);
                                    break;
                                case "RARP":
                                    criterion = new EthTypeCriterion(EtherType.RARP);
                                    break;
                                case "APPLETALK":
                                    criterion = new EthTypeCriterion(EtherType.APPLETALK);
                                    break;
                                case "PPPOE_DISCOVERY_STAGE":
                                    criterion = new EthTypeCriterion(EtherType.PPPOE_DISCOVERY_STAGE);
                                    break;
                                case "PPPOE_SESSION_STAGE":
                                    criterion = new EthTypeCriterion(EtherType.PPPOE_SESSION_STAGE);
                                    break;
                                default:
                                    throw new IllegalArgumentException();
                            }
                        }

                        // Add the criterion
                        criteria.addCriterion(criterion);
                        break;

                    // OF Packet Type
                    case "packetType":

                        if (type == JsonValue.ValueType.STRING)
                        {
                            String valueString = ((JsonString) value).getString().toUpperCase();
                            OFType ofType = OFType.valueOf(valueString);
                            criterion = new PacketTypeCriterion(ofType);
                        }

                        criteria.addCriterion(criterion);
                        break;

                    default:
                        System.out.println("key: " + key + " type: " + type + " value: " + value);
                }
            }

            return criteria;
        }
    }
}

