package edu.svv.fuzzsdn.fuzzer.instructions.criteria;


import org.projectfloodlight.openflow.protocol.OFMessage;
import org.projectfloodlight.openflow.protocol.OFType;

public class PacketTypeCriterion extends Criterion<OFType>
{
    // ===== ( Constructor ) ===========================================================================================

    public PacketTypeCriterion(OFType... values)
    {
        super(OFType.class, values);
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * See {@link Criterion#isSatisfied}
     */
    public boolean isSatisfied(OFMessage msg)
    {
        return values.contains(msg.getType());
    }
}

