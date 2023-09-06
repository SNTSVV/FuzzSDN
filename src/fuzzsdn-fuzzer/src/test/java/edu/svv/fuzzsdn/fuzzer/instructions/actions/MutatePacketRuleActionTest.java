package edu.svv.fuzzsdn.fuzzer.instructions.actions;

import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import edu.svv.fuzzsdn.common.utils.ByteUtil;
import edu.svv.fuzzsdn.common.utils.types.Pair;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;

import javax.json.Json;
import javax.json.JsonArrayBuilder;
import javax.json.JsonObjectBuilder;
import java.math.BigInteger;
import java.security.SecureRandom;
import java.util.HashSet;

class MutatePacketRuleActionTest
{
    private static final SecureRandom random = new SecureRandom();


    // ====== ( Testing the reader class ) =============================================================================

    @RepeatedTest(5)
    void Reader_ShouldReadCorrectIncludeHeaderBoolean_WhenReadingAJSONObject() throws ParsingException
    {
        boolean includeHeader = random.nextBoolean();
        JsonObjectBuilder testMsgBuilder = Json.createObjectBuilder();

        testMsgBuilder.add("intent", "MUTATE_PACKET_RULE");
        testMsgBuilder.add("target", "OF_PACKET");
        testMsgBuilder.add("includeHeader", includeHeader);

        // Read the action
        MutatePacketRuleAction action = MutatePacketRuleAction.READER.readJSON(testMsgBuilder.build());

        // Assertions
        Assertions.assertNotNull(action);
        Assertions.assertEquals(includeHeader, action.isHeaderIncluded());
    }

    @RepeatedTest(5)
    void Reader_ShouldReadTheCorrectMutationEnableBoolean_WhenReadingAJSONObject() throws ParsingException
    {
        boolean enableMutation = random.nextBoolean();
        JsonObjectBuilder testMsgBuilder = Json.createObjectBuilder();

        testMsgBuilder.add("intent", "MUTATE_PACKET_RULE");
        testMsgBuilder.add("target", "OF_PACKET");
        testMsgBuilder.add("enableMutation", enableMutation);

        // Read the action
        MutatePacketRuleAction action = MutatePacketRuleAction.READER.readJSON(testMsgBuilder.build());

        // Assertions
        Assertions.assertNotNull(action);
        Assertions.assertEquals(enableMutation, action.isMutationEnabled());
    }

    @RepeatedTest(5)
    void Reader_ShouldReadTheCorrectMutationRateMultiplier_WhenReadingAJSONObjectAndMutationIsEnabled() throws ParsingException
    {
        double mutationRateMultiplier = 0.1 + (5.0 - 0.1) * random.nextDouble();
        JsonObjectBuilder testMsgBuilder = Json.createObjectBuilder();

        testMsgBuilder.add("intent", "MUTATE_PACKET_RULE");
        testMsgBuilder.add("target", "OF_PACKET");
        testMsgBuilder.add("enableMutation", true);
        testMsgBuilder.add("mutationRateMultiplier", mutationRateMultiplier);

        // Read the action
        MutatePacketRuleAction action = MutatePacketRuleAction.READER.readJSON(testMsgBuilder.build());

        // Assertions
        Assertions.assertNotNull(action);
        Assertions.assertEquals(mutationRateMultiplier, action.getMutationRateMultiplier());
    }



    @RepeatedTest(10)
    void Reader_ShouldHaveCorrectNumberOfConditionsInRule_WhenReadingAJSONObject() throws ParsingException
    {
        JsonObjectBuilder testMsgBuilder = Json.createObjectBuilder();
        int cdtCount = random.nextInt(256);

        testMsgBuilder.add("intent", "MUTATE_PACKET_RULE");
        testMsgBuilder.add("target", "OF_PACKET");
        testMsgBuilder.add("includeHeader", false);

        JsonArrayBuilder ruleArrayBuilder = Json.createArrayBuilder();
        for (int i=0 ; i < cdtCount ; i++)
        {
            ruleArrayBuilder.add(Json.createObjectBuilder()
                    .add("field", "dummy_field_" + i)
                    .add("range", Json.createArrayBuilder()
                            .add(Json.createArrayBuilder().add(0).add(1)))
            );
        }

        // Create the rule object
        testMsgBuilder
                .add("rule", Json.createObjectBuilder()
                        .add("id"       , random.nextInt(99999))
                        .add("clauses"  , ruleArrayBuilder)
        );

        // Read the action
        MutatePacketRuleAction action = MutatePacketRuleAction.READER.readJSON(testMsgBuilder.build());

        // Assertions
        Assertions.assertNotNull(action);
        Assertions.assertEquals(cdtCount, action.getClauses().size());
    }

    @Test
    void Reader_ShouldCreateRuleWithConditionsWithCorrectRanges_WhenReadingAJSONObject() throws ParsingException
    {
        JsonObjectBuilder testMsgBuilder = Json.createObjectBuilder();
        HashSet<Pair<BigInteger>> ranges = new HashSet<>();
        for (int i=0 ; i < random.nextInt(256); i++ )
        {
            ranges.add(
                    new Pair<>(
                            ByteUtil.randomBigInteger(BigInteger.ZERO, new BigInteger("10000")),
                            ByteUtil.randomBigInteger(BigInteger.ZERO, new BigInteger("10000"))
                    )
            );
        }

        testMsgBuilder.add("intent", "MUTATE_PACKET_RULE");
        testMsgBuilder.add("target", "OF_PACKET");
        testMsgBuilder.add("includeHeader", false);

        // Add the conditions
        JsonObjectBuilder cdtBuilder = Json.createObjectBuilder().add("field", "dummy_field");
        JsonArrayBuilder rangesBuilder = Json.createArrayBuilder();

        for (Pair<BigInteger> range : ranges)
        {
            rangesBuilder.add(Json.createArrayBuilder()
                    .add(range.left)
                    .add(range.right));
        }
        cdtBuilder.add("range", rangesBuilder);

        // Create the rule object
        testMsgBuilder
                .add("rule", Json.createObjectBuilder()
                        .add("id"       , random.nextInt(99999))
                        .add("clauses"  , Json.createArrayBuilder()
                                .add(cdtBuilder))
                );

        // Read the action
        MutatePacketRuleAction action = MutatePacketRuleAction.READER.readJSON(testMsgBuilder.build());

        System.out.println(action);
        // Assertions
        Assertions.assertNotNull(action);
        Assertions.assertTrue(action.getClauses().iterator().next().getRange().containsAll(ranges));
    }

}