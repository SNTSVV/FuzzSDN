package edu.svv.fuzzsdn.common.utils.types;


/**
 * An unsigned 8-bit Integer
 */
public final class UInt8
{
    private final static byte ZERO_VAL = 0;
    public final static UInt8 ZERO = new UInt8(ZERO_VAL);

    private static final byte NO_MASK_VAL = (byte) 0xFF;
    public static final UInt8 NO_MASK = new UInt8(NO_MASK_VAL);
    public static final UInt8 FULL_MASK = ZERO;

    private final byte raw;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Create a new {@link UInt8} object from a signed byte value
     * @param signedValue the signed byte value
     */
    public UInt8(byte signedValue)
    {
        this.raw = signedValue;
    }

    /**
     * Create a new {@link UInt8} object from a signed byte value
     * @param unsignedValue the unsigned short value
     */
    public UInt8(short unsignedValue)
    {
        this.raw = toSigned(unsignedValue);
    }


    // ===== ( Getters ) ===============================================================================================

    /**
     * Get the unsigned value of the {@link UInt8} Object
     * @return the unsigned short value
     */
    public short getUnsigned()
    {
        return toUnsigned(raw);
    }

    /**
     * Get the signed value of the {@link UInt8} Object
     * @return the signed byte value
     */
    public byte getSigned()
    {
        return raw;
    }

    // ===== ( Static Methods ) ========================================================================================

    /**
     * Cast a signed short value to an unsigned short value.
     * @return the unsigned short value
     */
    public static short toUnsigned(final short value)
    {
        return (short) (value & NO_MASK_VAL);
    }

    /**
     * Cast a signed byte value to an unsigned short value.
     * @return the unsigned short value
     */
    public static short toUnsigned(final byte i)
    {
        return (short) (i & NO_MASK_VAL);
    }

    /**
     * Cast an unsigned short value to a signed byte value.
     * @return the signed short value
     */
    public static byte toSigned(final short l)
    {
        return (byte) l;
    }

    // ===== ( java.lang.Object Override ) =============================================================================


    /**
     * See {@link Object#toString()}
     */
    @Override
    public String toString()
    {
        return String.format("0x%02x", raw);
    }

    /**
     * See {@link Object#hashCode()}
     */
    @Override
    public int hashCode()
    {
        return 31 * raw;
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

        UInt8 other = (UInt8) obj;
        return raw == other.raw;
    }

}
