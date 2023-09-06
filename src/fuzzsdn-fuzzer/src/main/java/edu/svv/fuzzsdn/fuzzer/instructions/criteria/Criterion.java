package edu.svv.fuzzsdn.fuzzer.instructions.criteria;

import org.projectfloodlight.openflow.protocol.OFMessage;

import java.util.*;

public abstract class Criterion<F>
{
    protected Set<F>    values;
    protected Class<F>  type;

    // ===== ( Constructor ) ===========================================================================================

    @SafeVarargs
    public Criterion(Class<F> type, F... values)
    {
        this.type = type;
        this.values = new HashSet<>();
        if (values.length > 0)
            Collections.addAll(this.values, values);
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Get the values that should match the criterion.
     *
     * @return the {@link Collection} of values
     */
    public Collection<F> getValues()
    {
        return this.values;
    }

    /**
     * Determine if the criterion is satisfied by an OpenFlow Message.
     *
     * @param msg the {@link OFMessage} that should satisfy the criterion.
     * @return true if it satisfied, false otherwise.
     */
    abstract public boolean isSatisfied(OFMessage msg);

    // ===== ( Object Overrides ) ======================================================================================

    /**
     * See {@link Object#toString}
     */
    @Override
    public String toString()
    {
        boolean first = true;
        StringBuilder sb = new StringBuilder();

        // Print the type
        sb.append("{\"type\":\"").append(this.type.getSimpleName()).append("\",");

        // Print the values
        sb.append("\"values\":[");
        for (F value : values)
        {
            if (first)
                first = false;
            else
                sb.append(", ");
            sb.append("\"").append(value.toString()).append("\"");
        }
        sb.append("]}");

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
        else if (!(o instanceof Criterion<?>))
            result = false;
        else
        {
            Criterion<?> other = (Criterion<?>) o;
            result = Objects.equals(this.values, other.getValues());
        }

        return result;
    }

    /**
     * Override of {@link Object#hashCode} so the hashCode is the same when the values are the same.
     */
    @Override
    public int hashCode()
    {
        return Objects.hash(this.values);
    }

}
