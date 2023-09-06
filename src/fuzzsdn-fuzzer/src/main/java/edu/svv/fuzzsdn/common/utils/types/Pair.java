package edu.svv.fuzzsdn.common.utils.types;

import java.text.MessageFormat;
import java.util.Objects;

/**
 * A convenience class to represent pairs (tuples of 2 values)
 * @param <T> the type to be used by the pair
 */
public class Pair<T>
{
    // ===== ( Members ) ===============================================================================================

    public final T left;
    public final T right;

    // ===== ( Constructors ) ==========================================================================================

    public Pair(T left, T right)
    {
        this.left = left;
        this.right = right;
    }

    // ===== ( Public Methods ) ========================================================================================

    /**
     * String representation of this Pair. See {@link Object#toString}
     */
    @Override
    public String toString()
    {
        return MessageFormat.format("Pair({0}, {1})", this.left, this.right);
    }

    /**
     * Test this Pair for equality with another Object.
     * If the Object to be tested is not a Pair or is null, then this method returns false.
     * Two Pairs are considered equal if and only if both the left values and right values are equal.
     * See {@link Object#equals(Object)}
     */
    @Override
    public boolean equals(Object o)
    {
        boolean result;
        if (o == this)
            result = true;
        else if (!(o instanceof Pair<?>))
            result = false;
        else
        {
            Pair<?> other = (Pair<?>) o;
            result = Objects.equals(this.left, other.left)
                    && Objects.equals(this.right, other.right);
        }

        return result;
    }

    /**
     * Generate a hash code for this Pair.
     * The hash code is calculated using both the left and right of the Pair.
     * See {@link Object#hashCode}.
     */
    @Override
    public int hashCode()
    {
        return Objects.hash(this.left, this.right);
    }

}