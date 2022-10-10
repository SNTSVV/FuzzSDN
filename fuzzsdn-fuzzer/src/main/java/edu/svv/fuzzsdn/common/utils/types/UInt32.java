package edu.svv.fuzzsdn.common.utils.types;


/**
 * An unsigned 32-bit Integer
 */
public final class UInt32
{
    private final static int ZERO_VAL = 0;
    public final static UInt32 ZERO = new UInt32(ZERO_VAL);

    private static final long NO_MASK_VAL = 0xFFFFFFL;
    public static final UInt32 NO_MASK = new UInt32(NO_MASK_VAL);
    public static final UInt32 FULL_MASK = ZERO;

    private final int raw;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Create a new {@link UInt32} object from a signed int value
     * @param signedValue the signed int value
     */
    public UInt32(int signedValue)
    {
        this.raw = signedValue;
    }

    /**
     * Create a new {@link UInt32} object from a signed int value
     * @param unsignedValue the unsigned long value
     */
    public UInt32(long unsignedValue)
    {
        this.raw = toSigned(unsignedValue);
    }


    // ===== ( Getters ) ===============================================================================================

    /**
     * Get the unsigned value of the {@link UInt32} Object
     * @return the unsigned long value
     */
    public long getUnsigned()
    {
        return toUnsigned(raw);
    }

    /**
     * Get the signed value of the {@link UInt32} Object
     * @return the signed int value
     */
    public int getSigned()
    {
        return raw;
    }

    // ===== ( Static Methods ) ========================================================================================

    /**
     * Cast a signed long value to an unsigned long value.
     * @return the unsigned long value
     */
    public static long toUnsigned(final long value)
    {
        return value & NO_MASK_VAL;
    }

    /**
     * Cast a signed int value to an unsigned long value.
     * @return the unsigned long value
     */
    public static long toUnsigned(final int i)
    {
        return i & NO_MASK_VAL;
    }

    /**
     * Cast an unsigned long value to a signed int value.
     * @return the signed long value
     */
    public static int toSigned(final long l)
    {
        return (int) l;
    }

    // ===== ( java.lang.Object Override ) =============================================================================


    /**
     * See {@link Object#toString()}
     */
    @Override
    public String toString()
    {
        return String.format("0x%08x", raw);
    }

    /**
     * See {@link Object#hashCode()}
     */
    @Override
    public int hashCode()
    {
        return 31 + raw;
    }

    /**
     * See {@link Object#equals(Object)}
     */
    @Override
    public boolean equals(Object obj)
    {
        if (this == obj)
            return true;
        if (obj == null)
            return false;
        if (getClass() != obj.getClass())
            return false;

        UInt32 other = (UInt32) obj;
        return raw == other.raw;
    }

}
