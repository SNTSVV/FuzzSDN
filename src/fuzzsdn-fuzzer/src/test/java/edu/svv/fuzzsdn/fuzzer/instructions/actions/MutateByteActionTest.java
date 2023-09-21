package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;
import java.io.StringReader;

// TODO: Test Incorrect Keys
class MutateByteActionTest
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

    @Test
    void Builder_ShouldCreateCorrectAction()
    {
        MutateBytesAction actionWithHeader = new MutateBytesAction.Builder()
                .includeHeader(true)
                .build();

        MutateBytesAction actionWithoutHeader = new MutateBytesAction.Builder()
                .includeHeader(false)
                .build();


        Assertions.assertEquals(Action.Intent.MUTATE_BYTES, actionWithHeader.getIntent());
        Assertions.assertEquals(Action.Intent.MUTATE_BYTES, actionWithoutHeader.getIntent());
        Assertions.assertEquals(Action.Target.OF_PACKET, actionWithHeader.getTarget());
        Assertions.assertEquals(Action.Target.OF_PACKET, actionWithoutHeader.getTarget());
        Assertions.assertTrue(actionWithHeader.isHeaderIncluded());
        Assertions.assertFalse(actionWithoutHeader.isHeaderIncluded());
    }

    // ===== ( Reader Methods ) ========================================================================================

    @Test
    void Reader_ShouldReadCorrectAction_WhenReadingAJSONObject()
    {
        JsonObject jsonObject = jsonFromString(
                "{" +
                "\"intent\":\"mutate_bytes\"," +
                "\"includeHeader\":true" +
                "}");

        MutateBytesAction action = null;
        try
        {
            action = MutateBytesAction.READER.readJSON(jsonObject);
        }
        catch (ParsingException ignored) { } // Exception throwing is not tested here

        Assertions.assertNotNull(action);
        Assertions.assertTrue(action.isHeaderIncluded());
    }
}