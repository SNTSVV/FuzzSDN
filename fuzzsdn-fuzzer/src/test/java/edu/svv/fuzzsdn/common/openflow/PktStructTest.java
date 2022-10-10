package edu.svv.fuzzsdn.common.openflow;

import edu.svv.fuzzsdn.common.utils.ByteUtil;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import javax.json.JsonArray;
import javax.json.JsonObject;
import java.math.BigInteger;
import java.util.Arrays;
import java.util.Collection;
import java.util.HashSet;
import java.util.Iterator;

/**
 * Unit test for PktStruct class
 */
class PktStructTest
{

    @Test
    void byteLength_ShouldReturnCorrectLength()
    {
        PktStruct dummy_OFPktStruct = new PktStruct(
                new PktStruct.Field("dummy_1", 0, 1, true, 0b10101010),
                new PktStruct.Field("dummy_2", 0, 1, true, 0b01010101),
                new PktStruct.Field("dummy_3", 1, 2)
        );

        Assertions.assertEquals(3, dummy_OFPktStruct.byteLength());



        int mask = 0b1;
        int maxValue = mask;
        while ((maxValue & 1) == 0)
            maxValue = maxValue >> 1;
        System.out.println(BigInteger.valueOf(maxValue).toString(2));

        BigInteger oldFieldValue = BigInteger.valueOf(255);
        BigInteger bitMask = BigInteger.valueOf(mask);
        BigInteger max = BigInteger.valueOf(maxValue);
        BigInteger newFieldValue = ByteUtil.randomBigInteger(BigInteger.ZERO, max);

        newFieldValue = oldFieldValue.andNot(bitMask).or(newFieldValue);

        System.out.println("old val: " + oldFieldValue.toString(2));
        System.out.println("new val: " + newFieldValue.toString(2));
        System.out.println("mask: "    + bitMask.toString(2));


    }

    @Test
    void getByIndex_returnCorrectField_Equals()
    {
        PktStruct dummy_OFPktStruct = new PktStruct(
                new PktStruct.Field("dummy_1", 0, 10),
                new PktStruct.Field("dummy_2", 11, 13),
                new PktStruct.Field("dummy_3", 14, 30)
        );

        Assertions.assertEquals(dummy_OFPktStruct.getByIndex(0).name, "dummy_1");
        Assertions.assertEquals(dummy_OFPktStruct.getByIndex(1).name, "dummy_2");
        Assertions.assertEquals(dummy_OFPktStruct.getByIndex(2).name, "dummy_3");
    }

    @Test
    void getByIndex_outOfBound_throwsException()
    {
        Assertions.assertThrows(IndexOutOfBoundsException.class, () -> {
            PktStruct dummy_OFPktStruct = new PktStruct(new PktStruct.Field("dummy_1", 0, 10));
            dummy_OFPktStruct.getByIndex(2);
        });

    }

    @Test
    void getIndexOfField_ShouldGiveCorrectValue_WhenFieldExistsInThePktStruct()
    {
        PktStruct dummyOFPktStruct = new PktStruct(
                new PktStruct.Field("dummy_1", 0, 10),
                new PktStruct.Field("dummy_2", 11, 13),
                new PktStruct.Field("dummy_3", 14, 30),
                new PktStruct.Field("dummy_4", 24, 10),
                new PktStruct.Field("dummy_5", 37, 13),
                new PktStruct.Field("dummy_6", 50, 30)
        );


        Assertions.assertEquals(5, dummyOFPktStruct.getIndexOfField("dummy_6"));
        Assertions.assertEquals(4, dummyOFPktStruct.getIndexOfField("dummy_5"));
        Assertions.assertEquals(3, dummyOFPktStruct.getIndexOfField("dummy_4"));
        Assertions.assertEquals(2, dummyOFPktStruct.getIndexOfField("dummy_3"));
        Assertions.assertEquals(1, dummyOFPktStruct.getIndexOfField("dummy_2"));
        Assertions.assertEquals(0, dummyOFPktStruct.getIndexOfField("dummy_1"));
    }

    @Test
    void hasField_canFindFields_True()
    {
        PktStruct dummy_OFPktStruct = new PktStruct(
                new PktStruct.Field("dummy_1", 0, 10),
                new PktStruct.Field("dummy_2", 11, 13),
                new PktStruct.Field("dummy_3", 14, 30)
        );

        Assertions.assertTrue(dummy_OFPktStruct.hasField("dummy_1"));
        Assertions.assertTrue(dummy_OFPktStruct.hasField("dummy_2"));
        Assertions.assertTrue(dummy_OFPktStruct.hasField("dummy_3"));
    }

    @Test
    void hasField_cannotFindFields_False()
    {
        PktStruct dummy_OFPktStruct = new PktStruct(new PktStruct.Field("dummy_exist", 0, 10));
        Assertions.assertFalse(dummy_OFPktStruct.hasField("dummy_not_exist"));
    }

    @Test
    void getFields_fieldCollectionInOrder_Equals()
    {
        PktStruct dummy_OFPktStruct = new PktStruct(
                        new PktStruct.Field("dummy_1", 0, 10),
                        new PktStruct.Field("dummy_2", 11, 13),
                        new PktStruct.Field("dummy_3", 14, 30)
        );

        Collection<String> returned_fields = dummy_OFPktStruct.getFields();

        Iterator<String> it = returned_fields.iterator();
        Assertions.assertEquals(it.next(), "dummy_1");
        Assertions.assertEquals(it.next(), "dummy_2");
        Assertions.assertEquals(it.next() , "dummy_3");
    }

    @Test
    void last_ShouldReturnLastField_Equals()
    {
        PktStruct dummy_OFPktStruct = new PktStruct(
                new PktStruct.Field("dummy_1", 0, 1, true, 0b10101010),
                new PktStruct.Field("dummy_2", 0, 1, true, 0b01010101),
                new PktStruct.Field("dummy_3", 1, 2),
                new PktStruct.Field("dummy_last", 3, 1, true, 0b01010101)
        );
        PktStruct.Field lastField = new PktStruct.Field("dummy_last", 3, 1, true, 0b01010101);
        Assertions.assertEquals(lastField, dummy_OFPktStruct.last());
    }


    @Test
    void toJSON_ShouldCreateCorrectJSONObject_WhenCallingTheMethod()
    {
        HashSet<PktStruct.Field> fields = new HashSet<>(Arrays.asList(
                new PktStruct.Field("dummy_1", 0, 10),
                new PktStruct.Field("dummy_2", 11, 13),
                new PktStruct.Field("dummy_3", 14, 30),
                new PktStruct.Field("dummy_4", 24, 10),
                new PktStruct.Field("dummy_5", 37, 13),
                new PktStruct.Field("dummy_6", 50, 30)
        ));


        PktStruct dummy_OFPktStruct = new PktStruct(fields);

        JsonObject jObj = dummy_OFPktStruct.toJSON();
        JsonObject fieldObj;

        Assertions.assertTrue(jObj.containsKey("fields"));
        JsonArray jArray = jObj.getJsonArray("fields");
        int i=0;
        for (PktStruct.Field f: fields)
        {
            fieldObj = jArray.getJsonObject(i);
            Assertions.assertEquals(f.name, fieldObj.getString("name"));
            Assertions.assertEquals(f.offset, fieldObj.getInt("offset"));
            Assertions.assertEquals(f.length, fieldObj.getInt("length"));
            i++;
        }
    }
}