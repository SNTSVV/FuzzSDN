package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import org.projectfloodlight.openflow.protocol.OFMessage;

import javax.annotation.Nonnull;
import javax.annotation.Nullable;
import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonObjectBuilder;
import java.util.Objects;

public abstract class Action
{

    // ===== ( Members ) ===============================================================================================

    protected Intent intent;
    protected Target target;

    // ===== ( Constructors ) ==========================================================================================

    public Action(Intent type, Target target)
    {
        this.intent = type;
        this.target = target;
    }

    protected Action(Builder<?> b)
    {
        this.intent = b.intent;
        this.target = b.target;
    }

    // ===== ( Getters ) ===========================================================================================

    /**
     * Get the type of action to be performed
     *
     * @return the type of action
     */
    public Intent getIntent()
    {
        return this.intent;
    }

    /**
     * Get the type of action to be performed
     *
     * @return the type of action
     */
    public Target getTarget()
    {
        return this.target;
    }


    /**
     * Determine if the action can be applied to the given OFMessage
     *
     * @param msg the OFMessage the action should be applied to
     * @return true if it can be applied, false otherwise
     */
    abstract public boolean canBeAppliedTo(OFMessage msg);

    // ===== ( Json Conversion )  ======================================================================================

    /**
     * Create a JSON object which represent the action
     *
     * @return a {@link JsonObject}
     */
     public JsonObject toJSON()
     {
         JsonObjectBuilder jObjBuilder = Json.createObjectBuilder();
         jObjBuilder.add("target", this.target.name);
         jObjBuilder.add("intent", this.intent.name);

         return jObjBuilder.build();
     }

    // ===== ( Object Overrides ) ======================================================================================

    /**
     * See {@link Object#toString}
     */
    @Override
    public String toString()
    {
        return "{" +
                "\"intent\":\"" + this.intent.name + "\", " +
                "\"target\":\"" + this.target.name + "\"" +
                "}";
    }


    /**
     * see {@link Object#equals(Object)}
     */
    // TODO: Rework the equals method
    @Override
    public boolean equals(Object o)
    {
        boolean result;
        if (o == this)
            result = true;
        else if (!(o instanceof Action))
            result = false;
        else
        {
            Action other = (Action) o;
            result = Objects.equals(this.intent, other.intent);
        }

        return result;
    }

    /**
     * Override of {@link Object#hashCode} so the hashCode is the same when the intent and target are the same.
     */
    @Override
    public int hashCode()
    {
        return Objects.hash(this.intent, this.target);
    }

    // ===== ( Reader ) ================================================================================================

    /**
     * An interface that read action data from different kind of objects
     * @param <T> The type of action of the reader should return
     */
    public interface Reader<T>
    {
        /**
         * Read an Action from a {@link JsonObject}
         * @param jsonObject the {@link JsonObject} the data should be read from
         * @return the read action
         *
         * @throws ParsingException if the format of the action is not the one intended
         */
        @Nullable
        T readJSON(@Nonnull JsonObject jsonObject) throws ParsingException;
    }

    // ===== ( Builder ) ===============================================================================================

    protected static abstract class Builder<T>
    {
        protected Intent intent;
        protected Target target;

        protected Builder() {}

        protected Builder<T> intent(Intent intent)
        {
            this.intent = intent;
            return this;
        }

        protected Builder<T> target(Target target)
        {
            this.target = target;
            return this;
        }

        public abstract T build();
    }

    // ===== ( Enums ) =================================================================================================

    /**
     * The type of intent of the action that should be performed.
     * I.e a drop action will aim to drop a message, a scramble_all to modify a message randomly, etc.
     */
    public enum Intent
    {
        MUTATE_PACKET("mutate_packet"),             // Mutate an entire packet
        MUTATE_PACKET_RULE("mutate_packet_rule"),   // Mutate a packet according to a rule
        MUTATE_FIELD("mutate_field"),               // Mutate a field
        MUTATE_BYTES("mutate_bytes");               // Mutate a byte in the packet

        public String name;

        Intent(String name)
        {
            this.name = name;
        }

        @Override
        public String toString()
        {
            return this.name;
        }

        public static Intent fromString(String value)
        {
            for(Intent v : values())
                if(v.name.equalsIgnoreCase(value))
                    return v;

            throw new IllegalArgumentException("Intent value for \"" + value + "\" does not exists.");
        }
    }

    /**
     * A list of fields that can be use for fuzzing
     */
    public enum Target
    {
        // Related to the Header of an openflow message
        OF_HEADER("header"),
        OF_HEADER_VERSION("header_version"),
        OF_HEADER_TYPE("header_type"),         // The packet type in the header of an OpenFlow message
        OF_HEADER_XID("header_xid"),

        //
        OF_PACKET("of_packet"),

        // Packet_In
        PACKET_IN_BUFFER_ID("packet_in_buffer_id"),
        PACKET_IN_REASON("packet_in_reason"),
        PACKET_IN_COOKIE("packet_in_buffer_id"),
        PACKET_IN_PAD("packet_in_reason"),

        // OpenFlow Payload Fields (Usable only by Packet In and Packet Out)
        DATA("data"),                   // Entire data Payload
        DATA_ETH_TYPE("data_eth_type"), // The Ethernet type of an ethernet packet
        DATA_ETH_SRC("data_eth_src"),   // The source MAC address of an Ethernet packet
        DATA_ETH_DST("data_eth_dst"),   // The destination MAC address of an Ethernet packet
        DATA_IP_PROTO("data_ip_proto"), // The IP Protocol of an IP packet
        DATA_IPV4_SRC("data_ipv4_src"), // The source address of an IPV4 packet
        DATA_IPV4_DST("data_ipv4_dst"), // The destination address of an IPV4 packet
        DATA_IPV6_SRC("data_ipv6_src"), // The source address of an IPV6 packet
        DATA_IPV6_DST("data_ipv6_dst"), // The destination address of an IPV6 packet
        DATA_TCP_SRC("data_tcp_src"),   // The source port of a TCP/IP packet
        DATA_TCP_DST("data_tcp_dst"),   // The destination port of a TCP/IP packet
        DATA_UDP_SRC("data_udp_src"),   // The source UDP port of an UDP/IP packet
        DATA_UDP_DST("data_udp_dst");   // The destination UDP port of an UDP/IP packet

        public String name;

        Target(String name)
        {
            this.name = name;
        }

        @Override
        public String toString()
        {
            return this.name;
        }
    }
}
