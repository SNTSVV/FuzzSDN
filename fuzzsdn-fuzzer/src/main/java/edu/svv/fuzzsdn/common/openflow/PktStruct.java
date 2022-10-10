package edu.svv.fuzzsdn.common.openflow;


import javax.json.Json;
import javax.json.JsonArrayBuilder;
import javax.json.JsonObject;
import javax.json.JsonObjectBuilder;
import java.util.Collection;
import java.util.Collections;
import java.util.Iterator;
import java.util.LinkedHashSet;


// TODO: Change the container so the fields are iterables by index
/**
 * A class that give the structure of an openflow packet
 */
public class PktStruct
{
    // Field subclass
    public static class Field
    {
        public String name;
        public final int offset;
        public final int length;
        public final boolean hasMask;
        public final int mask;

        // ===== ( Constructors ) ======================================================================================

        public Field(String name, int offset, int length)
        {
            this(name, offset, length, false, 0);
        }

        public Field(String name, int offset, int length, boolean hasMask, int mask)
        {
            this.name = name;
            this.offset = offset;
            this.length = length;

            if (!hasMask)
            {
                this.hasMask = false;
                this.mask = 0;
            }
            else
            {
                this.hasMask = true;
                this.mask    = mask;

                // Check that the mask is not bigger than the field
                int field_bit_length = 8*length;
                int mask_bit_length = (int) (Math.floor(Math.log(mask) / Math.log(2) + 1));
                if (mask_bit_length > field_bit_length)
                {
                    throw new IllegalArgumentException("bitmask of \"" + name + "\" is bigger than the bit-length of" +
                            " the field (expected: <=" + field_bit_length + ", got: " + mask_bit_length + ")");
                }
            }
        }

        // ===== ( Methods ) ===========================================================================================

        public int getBitLength()
        {
            if (this.hasMask)
            {
                return (int) (Math.floor(Math.log(mask) / Math.log(2) + 1));
            }
            else
            {
                return 8 * this.length;
            }
        }

        /**
         * Return the {@link JsonObject} corresponding to this field
         * @return the json representation of this field
         */
        public JsonObject toJSON()
        {
            JsonObjectBuilder jObj = Json.createObjectBuilder()
                    .add("name", this.name)
                    .add("offset", this.offset)
                    .add("length", this.length);

            if (this.hasMask)
            {
                jObj.add("mask", this.mask);
            }

            return jObj.build();

        }

        // ===== ( Overrides ) =========================================================================================

        @Override
        public String toString()
        {
            StringBuilder s = new StringBuilder("Field(name=" + this.name + ", offset=" + this.offset + ", length=" + this.length);
            if (this.hasMask)
                s.append(", mask=").append(this.mask);

            s.append(")");

            return s.toString();
        }

        /**
         * see {@link Object#equals(Object)}
         */
        @Override
        public boolean equals(Object o)
        {
            boolean result;

            // Checks the if the object is exactly the same (same reference)
            if (o == this)
                result = true;
                // Must be an instance of PktStruct
            else if (!(o instanceof Field))
                result = false;
                // Advanced checks
            else
            {
                // Cast to PktStruct
                Field other = (Field) o;
                // Must have the same name
                if (!this.name.equals(other.name))
                    result = false;
                // Must have the same offset
                else if (this.offset != other.offset)
                    result = false;
                // Must have the same length
                else if (this.length != other.length)
                    result = false;
                // Must have the same mask
                else
                    result = this.mask == other.mask;
            }
            return result;
        }

    }

    // ===== ( Class members ) =========================================================================================

    private final LinkedHashSet<Field> fields;

    // ===== ( Constructor ) ===========================================================================================

    /**
     * Default constructor. The order of fields is important
     * @param fields The link
     */
    public PktStruct(Field... fields)
    {
        this.fields = new LinkedHashSet<>();
        if (fields.length > 0)
        {
            Collections.addAll(this.fields, fields);
        }
    }

    /**
     * Default constructor. The order of fields is important
     * @param fields The li
     */
    public PktStruct(Collection<Field> fields)
    {
        this.fields = new LinkedHashSet<>();
        this.fields.addAll(fields);
    }

    // ===== ( Getters ) ===============================================================================================

    /**
     * @return a Collection of the fields withing the packet
     */
    public Collection<String> getFields()
    {
        LinkedHashSet<String> fields = new LinkedHashSet<>();
        for (Field f : this.fields)
            fields.add(f.name);

        return fields;
    }

    /**
     * @return The last field stored in the pktStruct
     */
    public Field last()
    {
        if (this.fields.stream().skip(this.fields.size()-1).findFirst().isPresent())
            return this.fields.stream().skip(this.fields.size()-1).findFirst().get();
        else
            return null;
    }

    /**
     * Get the size of the fields collection
     *
     * @return the number of field within the packet
     */
    public int size()
    {
        return this.fields.size();
    }

    public Field getByName(String field)
    {
        Field output = null;
        if (this.hasField(field))
        {
            for (Field f : this.fields)
                if (f.name.equalsIgnoreCase(field))
                {
                    output = f;
                    break;
                }
        }
        else
        {
            throw new IllegalArgumentException("Field: \"" + field + "\" does not exist in this packet structure");
        }

        return output;
    }

    public int getIndexOfField(String field)
    {
        int idx = 0;
        if (this.hasField(field))
        {
            Iterator<Field> iterator = fields.iterator();
            for (int i = 0; i < this.fields.size(); i++)
            {
                if (iterator.next().name.equalsIgnoreCase(field))
                    break;
                idx += 1;
            }
        }
        else
        {
            throw new IllegalArgumentException("Field: \"" + field + "\" does not exist in this packet structure");
        }

        return idx;
    }

    /**
     * Return a field by its index
     *
     * @param index the index of the field to get
     * @return the {@link Field} that is at the required index
     *
     * @throws IndexOutOfBoundsException when the index is greater that the number of fields - 1 or lower than 0
     */
    public Field getByIndex(int index)
    {
        if (index > this.fields.size() - 1)
            throw new IndexOutOfBoundsException("index " + index + " is out of bound (Fields length = " + this.fields.size() + ")");
        else if (index < 0)
            throw new IndexOutOfBoundsException("index should be >= 0 (got " + index + ")");

        Iterator<Field> iterator = fields.iterator();

        for (int i = 0; i < index; i++)
            iterator.next();

        return iterator.next();
    }

    // ===== ( Setters ) ===============================================================================================

    /**
     * Add fields to the packet structure
     * @param name the name of the field.
     * @param length length of the field in bytes.
     * @param hasMask whether a mask is present in the field.
     * @param mask value of the mask. Ignored if hasMask is false.
     * @return this object
     */
    public PktStruct add(String name, int length, boolean hasMask, int mask)
    {
        int offset = this.last().offset + this.last().length;
        Field newField;

        if (hasMask)
            newField = new PktStruct.Field(name, offset, length, true, mask);
        else
            newField = new PktStruct.Field(name, offset, length);

        return this.add(newField);
    }


    /**
     * Add fields to the packet structure
     * @param name Name of the field.
     * @param length length of the field.
     * @return this object
     */
    public PktStruct add(String name, int length)
    {
        return this.add(name, length, false, 0);
    }


    /**
     * Add fields to the packet structure
     * @param fields the list of {@link Field} to add to the structure
     * @return this object
     */
    public PktStruct add(Field... fields)
    {
        if (fields.length > 0)
            Collections.addAll(this.fields, fields);
        return this;
    }

    /**
     * Add another packet structure to the structure.
     *
     * @param pktStruct The {@link PktStruct} to add
     * @return a pointer to this object
     */
    public PktStruct add(PktStruct pktStruct)
    {
        return this.add(pktStruct, true);
    }

    /**
     * Add another packet structure to the structure.
     *
     * @param pktStruct The {@link PktStruct} to add
     * @param append Whether or not the field should be appended
     * @return a pointer to this object
     */
    public PktStruct add(PktStruct pktStruct, boolean append)
    {
        int offset = 0;
        if (append)
            offset = this.last().offset + this.last().length;

        for (Field f : pktStruct.fields)
        {
            if (!f.hasMask)
                this.fields.add(new Field(f.name, f.offset + offset, f.length));
            else
                this.fields.add(new Field(f.name, f.offset + offset, f.length, true, f.mask));
        }
        return this;
    }

    // ===== ( Methods ) ===============================================================================================

    /**
     * @return the calculated byte length of the packet
     */
    public int byteLength()
    {
        int lengthOfBytes = 0;
        int lengthOfBits  = 0;
        for (Field f : this.fields)
        {
            if (!f.hasMask)
                lengthOfBytes += f.length;
            else  // Count the number of bit assigned by the mask
            {
                int mask_copy = f.mask;
                while (mask_copy > 0)
                {
                    lengthOfBits += (mask_copy & 1);  // binary comparison
                    mask_copy = mask_copy >> 1; //binary shifting
                }
            }
        }
        return lengthOfBytes + (int) Math.ceil((float) lengthOfBits / 8);
    }

    /**
     * Find if the packet contains a field with a specific name
     *
     * @param name The name of the field to find
     * @return {@code true} if the field was found {@code false} otherwise
     */
    public boolean hasField(String name)
    {
        boolean found = false;

        for (Field field : this.fields)
        {
            if (field.name.equalsIgnoreCase(name))
            {
                found = true;
                break;
            }
        }
        return found;
    }

    /**
     * @return the JSON Object holding the description of the packet structure
     */
    public JsonObject toJSON()
    {
        JsonArrayBuilder jArray = Json.createArrayBuilder();
        for (Field f: this.fields)
        {
            jArray.add(f.toJSON());
        }

        return Json.createObjectBuilder().add("fields", jArray).build();
    }

    // ===== ( Override ) ==============================================================================================

    @Override
    public String toString()
    {
        StringBuilder sb = new StringBuilder("PktStruct(");

        boolean first = true;
        for (Field f : fields)
        {
            if (first)
                first = false;
            else
                sb.append(", ");
            sb.append("{").append(f.toString()).append("}");
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

        // Checks the if the object is exactly the same (same reference)
        if (o == this)
            result = true;
        // Must be an instance of PktStruct
        else if (!(o instanceof PktStruct))
            result = false;
        // Advanced checks
        else
        {
            // Cast to PktStruct
            PktStruct other = (PktStruct) o;
            // Must have the same number of fields
            if (this.size() != other.size())
                result = false;
            // Must have the same byteLength
            else if (this.byteLength() != other.byteLength())
                result = false;
            // Check every fields
            else
            {
                result = true;
                for (int i=0; i<this.size() ; i++)
                {
                    if (! this.getByIndex(i).equals(other.getByIndex(i)))
                    {
                        result = false;
                        break;
                    }
                }
            }

        }
        return result;
    }

}
