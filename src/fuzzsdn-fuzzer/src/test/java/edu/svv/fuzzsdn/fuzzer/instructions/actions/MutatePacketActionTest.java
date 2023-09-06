package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;
import java.io.StringReader;
import java.util.Random;

// TODO: Test Incorrect Keys
class MutatePacketActionTest
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

    @RepeatedTest(5)
    void Builder_ShouldCreateCorrectAction()
    {
        Random rd = new Random();
        boolean includeHeader = rd.nextBoolean();
        MutatePacketAction testAction = new MutatePacketAction.Builder()
                .includeHeader(includeHeader)
                .build();

        Assertions.assertEquals(Action.Intent.MUTATE_PACKET, testAction.getIntent());
        Assertions.assertEquals(Action.Target.OF_PACKET, testAction.getTarget());
        Assertions.assertEquals(includeHeader, testAction.includesHeader());
    }

    // ===== ( Reader Methods ) ========================================================================================

    @Test
    void Reader_ShouldReadCorrectAction_WhenReadingAJSONObject()
    {
        JsonObject jsonObject = jsonFromString("{" +
                "\"intent\":\"mutate_packet\"," +
                "\"includeHeader\":true" +
                "}");

        MutatePacketAction action = null;
        try
        {
            action = MutatePacketAction.READER.readJSON(jsonObject);
        }
        catch (ParsingException ignored) { } // Exception throwing is not tested here


        Assertions.assertNotNull(action);
        Assertions.assertTrue(action.includesHeader());
    }
}