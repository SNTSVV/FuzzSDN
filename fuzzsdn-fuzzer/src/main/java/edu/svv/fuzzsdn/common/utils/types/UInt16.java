package edu.svv.fuzzsdn.common.utils.types;


/**
 * An unsigned 16-bit Integer
 */
public final class UInt16
{
    private final static short ZERO_VAL = 0;
    public final static UInt16 ZERO = new UInt16(ZERO_VAL);

    private static final short NO_MASK_VAL = (short) 0xFFFF;
    public static final UInt16 NO_MASK = new UInt16(NO_MASK_VAL);
    public static final UInt16 FULL_MASK = ZERO;

    private final short raw;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Create a new {@link UInt16} object from a signed short value
     * @param signedValue the signed short value
     */
    public UInt16(short signedValue)
    {
        this.raw = signedValue;
    }

    /**
     * Create a new {@link UInt16} object from a signed short value
     * @param unsignedValue the unsigned int value
     */
    public UInt16(int unsignedValue)
    {
        this.raw = toSigned(unsignedValue);
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * Get the unsigned value of the {@link UInt16} Object
     * @return the unsigned int value
     */
    public int getUnsigned()
    {
        return toUnsigned(raw);
    }

    /**
     * Get the signed value of the {@link UInt16} Object
     * @return the signed short value
     */
    public short getSigned()
    {
        return raw;
    }

    // ===== ( Static Methods ) ========================================================================================

    /**
     * Cast a signed int value to an unsigned int value.
     * @return the unsigned int value
     */
    public static int toUnsigned(final int value)
    {
        return value & NO_MASK_VAL;
    }

    /**
     * Cast a signed short value to an unsigned int value.
     * @return the unsigned int value
     */
    public static int toUnsigned(final short i)
    {
        return i & NO_MASK_VAL;
    }

    /**
     * Cast an unsigned int value to a signed short value.
     * @return the signed int value
     */
    public static short toSigned(final int l)
    {
        return (short) l;
    }

    // ===== ( java.lang.Object Override ) =============================================================================


    /**
     * See {@link Object#toString()}
     */
    @Override
    public String toString()
    {
        return String.format("0x%04x", raw);
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

        UInt16 other = (UInt16) obj;
        return raw == other.raw;
    }

}
