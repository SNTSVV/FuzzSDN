package edu.svv.fuzzsdn.fuzzer.instructions.criteria;

import org.projectfloodlight.openflow.protocol.OFMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

public class CriteriaSet
{
    // ===== ( Members ) ===============================================================================================
    // Logger
    private static final Logger log = LoggerFactory.getLogger(CriteriaSet.class);

    // Instruction set
    private final Set<Criterion<?>> mCriteriaSet;

    // ===== ( Constructor ) ===========================================================================================

    public CriteriaSet(Criterion<?>... criteria)
    {
        // HashSet so we ensure that all instructions are unique.
        this.mCriteriaSet = new HashSet<>();

        // Add all criteria
        if (criteria.length > 0)
            Collections.addAll(this.mCriteriaSet, criteria);
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Determine if the criteria is satisfied by an OpenFlow Message.
     *
     * @param msg the {@link OFMessage} that should satisfy the criterion.
     * @return true if it satisfied, false otherwise.
     */
     public boolean isSatisfied(OFMessage msg)
     {
         boolean satisfied = true;
         for (Criterion<?> criterion : mCriteriaSet)
         {
             if (!criterion.isSatisfied(msg))
             {
                 satisfied = false;
                 break;  // Exit the loop
             }
         }

         return satisfied;
     }

    // ===== ( Setters ) ===============================================================================================

    /**
     * Adds a {@link Criterion} to the criteria object
     *
     * @param criterion the {@link Criterion}  to be stored
     * @return this CriteriaSet object
     */
    public CriteriaSet addCriterion(Criterion<?> criterion)
    {
        if (!mCriteriaSet.contains(criterion))
        {
            this.mCriteriaSet.add(criterion);
        }

        return this;
    }

    // ===== ( Object Overrides ) ======================================================================================

    /**
     * See {@link Object#toString}
     */
    @Override
    public String toString()
    {
        boolean first = true;
        StringBuilder sb = new StringBuilder("[");

        // Print the values
        for (Criterion<?> c : mCriteriaSet)
        {
            if (first)
                first = false;
            else
                sb.append(", ");
            sb.append(c.toString());
        }
        sb.append("]");

        return sb.toString();
    }

}
