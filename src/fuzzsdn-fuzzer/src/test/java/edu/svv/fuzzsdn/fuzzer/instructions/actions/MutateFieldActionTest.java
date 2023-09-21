package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import edu.svv.fuzzsdn.common.utils.types.Pair;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;
import java.io.StringReader;
import java.math.BigInteger;

// TODO: Test Incorrect Keys
class MutateFieldActionTest
{
    // ===== ( Helper Methods ) ========================================================================================

    JsonObject jsonFromString(String jsonObjectStr)
    {
        JsonReader jsonReader = Json.createReader(new StringReader(jsonObjectStr));
        JsonObject object = jsonReader.readObject();
        jsonReader.close();

        return object;
    }

    // ===== ( Builder Methods ) =======================================================================================

//    @RepeatedTest(10)
//    void Builder_ShouldCreateCorrectAction_WhenCreatingActionWithNumberOfFieldsAndMutateAllEqualsIsFalse()
//    {
//        Random rd = new Random();
//        int nbOfFieldsToFuzz = rd.nextInt(1000);
//        boolean includeHeader = rd.nextBoolean();
//        MutatePacketAction testAction = new MutatePacketAction.Builder()
//                .mutateAll(false)
//                .fixedCount(nbOfFieldsToFuzz)
//                .includeHeader(includeHeader)
//                .build();
//
//        Assertions.assertEquals(Action.Intent.MUTATE_PACKET, testAction.getIntent());
//        Assertions.assertEquals(Action.Target.OF_PACKET, testAction.getTarget());
//        Assertions.assertEquals(nbOfFieldsToFuzz , testAction.getFixedCount());
//        Assertions.assertEquals(includeHeader, testAction.includesHeader());
//    }
//
//    @Test
//    void Builder_ShouldThrowIllegalArgumentException_WhenCreatingActionWithNumberOfFieldsAndMutateAllisTrue()
//    {
//        Assertions.assertThrows(IllegalArgumentException.class, () -> {
//            MutatePacketAction testAction = new MutatePacketAction.Builder()
//                    .mutateAll(true)
//                    .fixedCount(1)
//                    .includeHeader(true)
//                    .build();
//        });
//    }

    // ===== ( Reader Methods ) ========================================================================================

    // TODO: Generate randomly fieldName and ranges
    @Test
    void Reader_ShouldReadCorrectAction_WhenReadingAJSONObjectWithRanges()
    {
        JsonObject jsonObject = jsonFromString("{"
                + "\"intent\":\"mutate_field\","
                + "\"fieldName\":\"test\","
                + "\"range\":["
                        + "[0, 1],"
                        + "[0,6],"
                        + "[4250, 9000]"
                    + "]"
                + "}"
        );

        MutateFieldAction action = null;
        try
        {
            action = MutateFieldAction.READER.readJSON(jsonObject);
        }
        catch (ParsingException ignored) {} // Exception throwing is not tested here
        System.out.println(action);
        Assertions.assertNotNull(action);
        Assertions.assertEquals(Action.Intent.MUTATE_FIELD, action.getIntent());
        Assertions.assertEquals("test", action.getFieldName());
        Assertions.assertEquals(3, action.getRanges().size());
        Assertions.assertTrue(action.getRanges().contains(new Pair<>(new BigInteger("0"), new BigInteger("1"))));
        Assertions.assertTrue(action.getRanges().contains(new Pair<>(new BigInteger("0"), new BigInteger("6"))));
        Assertions.assertTrue(action.getRanges().contains(new Pair<>(new BigInteger("4250"), new BigInteger("9000"))));

        System.out.println(action);
    }

    @Test
    void Reader_ShouldReadCorrectAction_WhenReadingAJSONObjectWithoutRanges()
    {
        JsonObject jsonObject = jsonFromString("{"
                + "\"intent\":\"mutate_field\","
                + "\"fieldName\":\"test\""
                + "}"
        );

        MutateFieldAction action = null;
        try
        {
            action = MutateFieldAction.READER.readJSON(jsonObject);
        }
        catch (ParsingException ignored) {} // Exception throwing is not tested here

        Assertions.assertNotNull(action);
        Assertions.assertEquals(Action.Intent.MUTATE_FIELD, action.getIntent());
        Assertions.assertEquals("test", action.getFieldName());
        Assertions.assertNull(action.getRanges());

        System.out.println(action);
    }
}