package edu.svv.fuzzsdn.fuzzer.instructions;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;
import java.io.StringReader;

class InstructionTest
{

    // ===== ( Helper Methods ) ========================================================================================

    JsonObject jsonFromString(String jsonObjectStr)
    {
        JsonReader jsonReader = Json.createReader(new StringReader(jsonObjectStr));
        JsonObject object = jsonReader.readObject();
        jsonReader.close();

        return object;
    }

    // ===== ( Reader ) ================================================================================================

    // TODO: Test the reader


}