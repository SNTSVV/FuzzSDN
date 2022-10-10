package edu.svv.fuzzsdn.fuzzer.instructions;

import edu.svv.fuzzsdn.fuzzer.instructions.actions.Action;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.MutatePacketAction;
import edu.svv.fuzzsdn.fuzzer.instructions.criteria.CriteriaSet;
import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.Test;

import javax.json.Json;
import javax.json.JsonObject;
import javax.json.JsonReader;
import java.io.StringReader;
import java.util.Collection;

class InstructionSetTest
{
    JsonObject jsonFromString(String jsonObjectStr)
    {
        JsonReader jsonReader = Json.createReader(new StringReader(jsonObjectStr));
        JsonObject object = jsonReader.readObject();
        jsonReader.close();

        return object;
    }

    @Test
    void Reader_ShouldReadCorrectInstructionSet_WhenReadingAJSONObject()
    {
        JsonObject jsonObject = jsonFromString(
                "{"
                + "     \"instructions\":["
                + "         {"
                + "             \"criteria\": ["
                + "                 {"
                + "                     \"packetType\": \"packet_in\","
                + "                     \"ethType\": \"arp\""
                + "                 }"
                + "             ],"
                + "             \"matchLimit\": 1,"
                + "             \"actions\": ["
                + "                 {"
                + "                     \"intent\": \"mutate_packet\","
                + "                     \"includeHeader\": false"
                + "                 }"
                + "             ]"
                + "         }"
                + "     ]"
                + "}"
        );

        InstructionSet instructionSet = null;
        try
        {
            instructionSet = InstructionSet.READER.readJSON(jsonObject);
        }
        catch (ParsingException ignored) { } // Exception throwing is not tested here

        // Check that the instruction set is created
        Assertions.assertNotNull(instructionSet);

        // Check that there is exactly 1 instruction
        Collection<Instruction> instructions = instructionSet.getInstructions();
        Assertions.assertNotNull(instructions);
        Assertions.assertFalse(instructions.isEmpty());
        Assertions.assertEquals(1, instructions.size());

        // Check that the instruction is correctly formatted
        Instruction instruction = instructions.iterator().next();

        // Check that the action is correctly formatted
        Collection<Action> actions = instruction.getActions();
        Assertions.assertNotNull(actions);
        Assertions.assertFalse(actions.isEmpty());
        Assertions.assertEquals(1, actions.size());


        Action actionToCheck = actions.iterator().next();
        Assertions.assertTrue(actionToCheck instanceof MutatePacketAction);
        Assertions.assertFalse(((MutatePacketAction) actionToCheck).includesHeader());

        // Check that criteria is correctly formatted
        Collection<CriteriaSet> criteriaSets = instruction.getCriteria();
        Assertions.assertNotNull(criteriaSets);
        Assertions.assertFalse(criteriaSets.isEmpty());
        Assertions.assertEquals(1, criteriaSets.size());
    }

}