package edu.svv.fuzzsdn.fuzzer.core.fuzzer;

import edu.svv.fuzzsdn.common.openflow.OFPktStruct;
import edu.svv.fuzzsdn.common.openflow.PktStruct;
import edu.svv.fuzzsdn.common.utils.ByteUtil;
import edu.svv.fuzzsdn.common.utils.types.Pair;
import edu.svv.fuzzsdn.fuzzer.Methods;
import edu.svv.fuzzsdn.fuzzer.Report;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.MutateBytesAction;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.MutateFieldAction;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.MutatePacketAction;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.MutatePacketRuleAction;
import io.netty.buffer.ByteBuf;
import io.netty.buffer.Unpooled;
import org.jetbrains.annotations.NotNull;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;
import org.pcap4j.packet.ArpPacket;
import org.pcap4j.packet.EthernetPacket;
import org.pcap4j.packet.namednumber.ArpHardwareType;
import org.pcap4j.packet.namednumber.ArpOperation;
import org.pcap4j.packet.namednumber.EtherType;
import org.pcap4j.util.MacAddress;
import org.projectfloodlight.openflow.protocol.*;
import org.projectfloodlight.openflow.protocol.action.OFAction;
import org.projectfloodlight.openflow.protocol.match.MatchField;
import org.projectfloodlight.openflow.protocol.ver13.OFFactoryVer13;
import org.projectfloodlight.openflow.protocol.ver14.OFActionsVer14;
import org.projectfloodlight.openflow.protocol.ver14.OFFactoryVer14;
import org.projectfloodlight.openflow.types.*;

import java.math.BigInteger;
import java.net.Inet4Address;
import java.net.UnknownHostException;
import java.security.SecureRandom;
import java.util.*;

class MethodsTest
{

    private static final SecureRandom random = new SecureRandom();

    // ===== ( Helper Functions ) ======================================================================================


    /**
     * Generate an OFPacketIn with an ARP Message as data
     * @return an {@link OFPacketIn}
     */
    private OFPacketIn dummyOFPacketIn()
    {
        OFFactory factory = OFFactoryVer13.INSTANCE;
        OFPacketIn.Builder packetInBuilder = factory.buildPacketIn();

        packetInBuilder
                .setXid(0x12345678)
                .setBufferId(OFBufferId.of(100))
                .setTotalLen(17000)
                .setReason(OFPacketInReason.ACTION)
                .setTableId(TableId.of(20))
                .setCookie(U64.parseHex("FEDCBA9876543210"))
                .setMatch(
                        factory.buildMatchV3()
                                .setExact(MatchField.ARP_OP, ArpOpcode.REQUEST)
                                .build()
                );

        // Build the arp message
        EthernetPacket ethPacket = null;
        try
        {
            EthernetPacket.Builder ethBuilder = new EthernetPacket.Builder()
                    .paddingAtBuild(true)
                    .type(EtherType.ARP)
                    .srcAddr(MacAddress.getByName("00:00:00:00:00:01"))
                    .dstAddr(MacAddress.getByName("00:00:00:00:00:02"))
                    .payloadBuilder(new ArpPacket.Builder()
                            .operation(ArpOperation.REQUEST)
                            .hardwareType(ArpHardwareType.ETHERNET)
                            .protocolType(EtherType.IPV4)
                            .srcHardwareAddr(MacAddress.getByName("00:00:00:00:00:01"))
                            .dstHardwareAddr(MacAddress.getByName("00:00:00:00:00:02"))
                            .srcProtocolAddr(Inet4Address.getByName("10.0.0.1"))
                            .dstProtocolAddr(Inet4Address.getByName("10.0.0.2"))
                            .hardwareAddrLength((byte) 6)
                            .protocolAddrLength((byte) 4)
                    );

            ethPacket = ethBuilder.build();
        }
        catch (UnknownHostException ignored) { }

        if (ethPacket == null) throw new AssertionError();
        packetInBuilder.setData(ethPacket.getRawData());
        return packetInBuilder.build();
    }

    /**
     * Generate an OFPacketOut with an ARP Message as data
     * @return an {@link OFPacketOut}
     */
    private OFPacketOut dummyOFPacketOut()
    {
        OFFactory factory = OFFactoryVer14.INSTANCE;
        OFPacketOut.Builder builder = factory.buildPacketOut();
        // Prepare the actions
        List<OFAction> actions = new java.util.ArrayList<>();
        actions.add(OFActionsVer14.INSTANCE.output(OFPort.ANY, 15));
        actions.add(OFActionsVer14.INSTANCE.copyTtlOut());
        actions.add(OFActionsVer14.INSTANCE.copyTtlIn());

        // Build the packet
        builder
                .setXid(0x12345678)
                .setBufferId(OFBufferId.of(100))
                .setInPort(OFPort.ofShort((short) 123))
                .setActions(actions)
                .setData(new byte[] { 97, 98, 99 } );

        // Build an arp message as data
        EthernetPacket ethPacket = null;
        try
        {
            EthernetPacket.Builder ethBuilder = new EthernetPacket.Builder()
                    .paddingAtBuild(true)
                    .type(EtherType.ARP)
                    .srcAddr(MacAddress.getByName("00:00:00:00:00:01"))
                    .dstAddr(MacAddress.getByName("00:00:00:00:00:02"))
                    .payloadBuilder(new ArpPacket.Builder()
                            .operation(ArpOperation.REQUEST)
                            .hardwareType(ArpHardwareType.ETHERNET)
                            .protocolType(EtherType.IPV4)
                            .srcHardwareAddr(MacAddress.getByName("00:00:00:00:00:01"))
                            .dstHardwareAddr(MacAddress.getByName("00:00:00:00:00:02"))
                            .srcProtocolAddr(Inet4Address.getByName("10.0.0.1"))
                            .dstProtocolAddr(Inet4Address.getByName("10.0.0.2"))
                            .hardwareAddrLength((byte) 6)
                            .protocolAddrLength((byte) 4)
                    );

            ethPacket = ethBuilder.build();
        }
        catch (UnknownHostException ignored) { }

        if (ethPacket == null) throw new AssertionError();
        builder.setData(ethPacket.getRawData());
        return builder.build();
    }

    /**
     * Generate a random packet
     * @return a byte array of the random packet
     */
    @NotNull
    private byte[] dummyPacket()
    {
        // Between 20 and 256 bytes
        int packetLength = 20 + random.nextInt(236);
        byte[] packet = new byte[packetLength];
        random.nextBytes(packet);
        return packet;
    }


    /**
     * Generate a random packet structure from a list of bytes
     * @return a {@link PktStruct} array of the random packet
     */
    public PktStruct dummyStruct(@NotNull byte[] packet)
    {
        List<Integer> load;
        int sum;

        do
        {
            int numberOfDraws = 2 + random.nextInt(packet.length / 2 - 2);
            int targetSum = packet.length;

            //random numbers
            load = new ArrayList<>();
            sum = 0;

            for (int i = 0 ; i < numberOfDraws ; i++)
            {
                int next = random.nextInt(targetSum) + 1;
                load.add(next);
                sum += next;
            }

            //scale to the desired target sum
            double scale = 1d * targetSum / sum;
            sum = 0;
            for (int i = 0 ; i < numberOfDraws ; i++)
            {
                load.set(i, (int) (load.get(i) * scale));
                sum += load.get(i);
            }

            //take rounding issues into account
            while (sum++ < targetSum)
            {
                int i = random.nextInt(numberOfDraws);
                load.set(i, load.get(i) + 1);
            }
        } while (load.contains(0));


        PktStruct pktStruct = new PktStruct();
        int offset = 0;
        for (int i=0; i < load.size(); i++)
        {
            pktStruct.add(new PktStruct.Field("field_" + i, offset, load.get(i)));
            offset += load.get(i);
        }

        return pktStruct;

    }

    // ===== ( mutatePacket Method Tests ) =============================================================================

    @Test
    void mutatePacket_ShouldNotModifyPacketLength_WhenAPacketIsMutated()
    {
        byte[] dummyPacket = dummyPacket();
        PktStruct dummyStruct = dummyStruct(dummyPacket);

        // Create a new scramble all action
        MutatePacketAction action = new MutatePacketAction.Builder()
                .includeHeader(true)
                .build();

        // Create a new ByteBuf that encapsulate the dummy message
        ByteBuf buffer = Unpooled.wrappedBuffer(dummyPacket);

        // Change the buffer
        Methods.mutatePacket(dummyStruct, buffer, action);
        byte[] fuzzedBytes = new byte[buffer.readableBytes()];
        buffer.readBytes(fuzzedBytes);

        // Assert the lengths are equals
        Assertions.assertEquals(dummyPacket.length, fuzzedBytes.length);
    }


    @RepeatedTest(100)
    void mutatePacket_ShouldMutateSomeFields_WhenIncludeHeaderIsTrue()
    {
        // Create a new scramble all action
        OFPacketIn ofPacketIn = dummyOFPacketIn();
        PktStruct pktStruct = OFPktStruct.fromOFMessage(ofPacketIn);

        // Create the Action
        MutatePacketAction action = new MutatePacketAction.Builder()
                .includeHeader(true)
                .build();

        // Put the message in a buffer
        ByteBuf buf = Unpooled.buffer();
        ofPacketIn.writeTo(buf);

        // Create the report object used to count the number of actions performed
        Report report = new Report();
        report.setCurrentAction(action);

        // Mutate the packet
        Methods.mutatePacket(pktStruct, buf, action, report);

        // Count the mutation operations performed
        int mutationOps = report.getMutations().get(action).size();

        Assertions.assertTrue(mutationOps > 0);
    }


    @RepeatedTest(100)
    void mutatePacket_ShouldMutateSomeFieldsExceptTheOpenFlowHeader_WhenIncludeHeaderIsFalse()
    {
        // Create a new scramble all action
        OFPacketIn ofPacketIn = dummyOFPacketIn();
        PktStruct pktStruct = OFPktStruct.fromOFMessage(ofPacketIn);

        // Create the mutation action
        MutatePacketAction action = new MutatePacketAction.Builder()
                .includeHeader(false)
                .build();

        // Create a byte array copy of the message that we store for later
        ByteBuf refBuf = Unpooled.buffer();
        ofPacketIn.writeTo(refBuf);
        ByteBuf buf = refBuf.copy();

        // Create the report object used to count the number of actions performed
        Report report = new Report();
        report.setCurrentAction(action);

        // Mutate the packet
        Methods.mutatePacket(pktStruct, buf, action, report);

        // Read the result of the fuzzed message
        buf.readerIndex(0);
        refBuf.readerIndex(0);
        byte[] original = new byte[refBuf.readableBytes()];
        byte[] fuzzed = new byte[buf.readableBytes()];
        refBuf.readBytes(original);
        buf.readBytes(fuzzed);

        // Evaluate the number of difference and if all the fields that needed to be fuzzed have been fuzzed properly
        int mutationOps = report.getMutations().get(action).size();

        // Assert that all the in the header are not modified
        PktStruct.Field f = pktStruct.getByIndex(4);
        byte[] oldValue = Arrays.copyOfRange(original, 0, f.offset);
        byte[] newValue = Arrays.copyOfRange(fuzzed, 0, f.offset);
        Assertions.assertArrayEquals(oldValue, newValue);

        // Assert that the number of differences is equal to the number of fields in the packet minus the header
        Assertions.assertTrue(mutationOps > 0);
        System.out.println(mutationOps);
    }


    @Test
    void mutatePacket_ShouldReturnCorrectHistory_WhenAPacketIsMutatedAndHistoryIsProvided()
    {
        byte[] dummyPacket = dummyPacket();
        PktStruct dummyStruct = dummyStruct(dummyPacket);

        // Create a new MutatePacket Action
        MutatePacketAction action = new MutatePacketAction.Builder()
                .includeHeader(true)
                .build();

        // Create a new ByteBuf that encapsulate the dummy message
        ByteBuf buffer = Unpooled.wrappedBuffer(dummyPacket);

        // Create the history object
        Report history = new Report();
        history.setInitialPacket(buffer);
        history.setPktStruct(dummyStruct);
        // Copy the history at this stage
        Report old_history = new Report(history);
        // Perform the mutation
        history.setCurrentAction(action);
        Methods.mutatePacket(dummyStruct, buffer, action, history);
        byte[] fuzzedBytes = new byte[buffer.readableBytes()];
        buffer.readBytes(fuzzedBytes);
        history.setFinalPacket(buffer);
        history.setEnd();

        // Assert that the history has properly changed
        Assertions.assertEquals(old_history.getStart(), history.getStart());
        Assertions.assertNotEquals(old_history.getEnd(), history.getEnd());
        Assertions.assertEquals(old_history.getPktStruct(), history.getPktStruct());
        Assertions.assertArrayEquals(old_history.getInitialPacket(), history.getInitialPacket());
        Assertions.assertFalse(Arrays.equals(old_history.getFinalPacket(), history.getFinalPacket()));
        // FIXME: The mutations are still copied in thr old history, the copy function must be corrected
        // Assertions.assertNotEquals(old_history.getMutations(), history.getMutations());
        Assertions.assertEquals(1, history.getMutations().size());
    }

    // ===== ( mutatePacketRule Method Tests ) =========================================================================

    @RepeatedTest(50)
    // TODO: Create bew method that test that the correct ranges are fuzzed
    void mutatePacketRule_ShouldMutateTheFieldsInTheRuleAndSomeOtherFields_WhenARuleIsSpecifiedWithASingleRangeConditions()
    {
        // Create a new scramble all action
        OFMessage ofPacket = null;
        switch (random.nextInt(2))
        {
            case 0:
                ofPacket = dummyOFPacketIn();
                break;
            case 1:
                ofPacket = dummyOFPacketOut();
                break;
        }

        // Build the structure
        PktStruct pktStruct = OFPktStruct.fromOFMessage(ofPacket);

        // Build the fields to mutate
        MutatePacketRuleAction.Builder mutPktRuleActionBld = new MutatePacketRuleAction.Builder();
        mutPktRuleActionBld.includeHeader(false);
        for (int i = 3 ; i < random.nextInt(pktStruct.size()) ; i++)
        {
            // Get a random field that will be the target of the test and create the action
            PktStruct.Field testedField = pktStruct.getByIndex(random.nextInt(pktStruct.size()));

            BigInteger minVal = BigInteger.ZERO;
            BigInteger maxVal = null;
            // Get the max value depending on the mask
            maxVal = BigInteger.TWO.pow(testedField.length * 8).subtract(BigInteger.ONE);
            if (testedField.hasMask)
            {
                // If the tested field has a mask then the it should be applied to maxVal
                BigInteger _mask = BigInteger.valueOf(testedField.mask);

                // get the number of trailing zeros in the mask
                int mask_copy = testedField.mask;
                int mtz = 0;
                while ((mask_copy & 1) == 0)
                {
                    mask_copy >>= 1;
                    mtz++;
                }
                // update maxVal
                maxVal = maxVal.and(_mask.shiftRight(mtz));
            }

            // Add the clause to the action
            mutPktRuleActionBld.addClause(testedField.name, new Pair<>(minVal, maxVal));
        }

        MutatePacketRuleAction mutPktRuleAction = mutPktRuleActionBld.build();

        // Create a byte array copy of the message that we store for later
        ByteBuf refBuf = Unpooled.buffer();
        ByteBuf buf = Unpooled.buffer();
        ofPacket.writeTo(buf);
        ofPacket.writeTo(refBuf);

        // Mutate the packet
        Methods.mutatePacketRule(pktStruct, buf, mutPktRuleAction);

        buf.readerIndex(0);
        refBuf.readerIndex(0);
        byte[] original = new byte[refBuf.readableBytes()];
        byte[] fuzzed = new byte[buf.readableBytes()];
        refBuf.readBytes(original);
        buf.readBytes(fuzzed);

        for (MutatePacketRuleAction.Clause c : mutPktRuleAction.getClauses())
        {
            PktStruct.Field testedField = pktStruct.getByName(c.getField());
            Pair<BigInteger> testRange = c.getRange().iterator().next();

            BigInteger oldValue = new BigInteger(
                    1,
                    Arrays.copyOfRange(
                            original,
                            testedField.offset,
                            testedField.offset + testedField.length
                    )
            );
            BigInteger newValue = new BigInteger(
                    1,
                    Arrays.copyOfRange(
                            fuzzed,
                            testedField.offset,
                            testedField.offset + testedField.length
                    )
            );

            // System.out.println("Tested field: " + testedField.toString());
            // System.out.println(testedField.hasMask);
            if (testedField.hasMask)
            {
                int mask_copy = testedField.mask;
                int mtz = 0;
                while ((mask_copy & 1) == 0)
                {
                    mask_copy >>= 1;
                    mtz++;
                }

                // System.out.println("expected range: " + testRange);
                // System.out.println("mutation effect (unmasked): " + oldValue.toString(2) + " -> " + newValue.toString(2));
                // oldValue = oldValue.and(BigInteger.valueOf(testedField.mask));
                newValue = newValue.and(BigInteger.valueOf(testedField.mask)).shiftRight(mtz);
                // System.out.println("mutation effect (masked): " + oldValue.toString() + " (" + oldValue.toString(2) + ") -> " + newValue.toString(2) + " (" + newValue.toString() + ")");
            }
            else
            {
                newValue = new BigInteger(
                        1,
                        Arrays.copyOfRange(
                                fuzzed,
                                testedField.offset,
                                testedField.offset + testedField.length
                        )
                );
                // System.out.println("expected range: " + testRange);
                // System.out.println("mutation effect: " + oldValue + " -> " + newValue);
            }

            // That the field value haas changed and that new value is between the correct range
            // We use "not equals" to simulate "<=" and ">="
            Assertions.assertNotEquals(-1, newValue.compareTo(testRange.left), newValue.toString() + "<" + testRange.left);
            Assertions.assertNotEquals(1, newValue.compareTo(testRange.right), newValue.toString() + ">" + testRange.right);
        }
    }


    @RepeatedTest(50)
    void mutatePacketRule_ShouldCorrectlyMutateTheFieldsInTheRule_WhenARuleIsSpecifiedWithValueConditions()
    {
        // Create a random packet
        OFMessage ofMessage = null;
        switch (random.nextInt(2))
        {
            case 0:
                ofMessage = dummyOFPacketIn();
                break;

            case 1:
                ofMessage = dummyOFPacketOut();
                break;
        }

        PktStruct pktStruct = OFPktStruct.fromOFMessage(ofMessage);

        // Get a random field that will be the target of the test and create the action
        PktStruct.Field testedField = pktStruct.getByIndex(random.nextInt(pktStruct.size()));
        BigInteger testValue;
        int mtz = 0;
        if (testedField.hasMask)
        {
            int _maxInt = testedField.mask;
            while ((_maxInt & 1) == 0)
            {
                _maxInt >>= 1;
                mtz++;
            }
            testValue = ByteUtil.randomBigInteger(BigInteger.ZERO, BigInteger.valueOf(_maxInt));
        }
        else
        {
            testValue = ByteUtil.randomBigInteger(
                    BigInteger.ZERO,
                    BigInteger.TWO.pow(testedField.length * 8).subtract(BigInteger.ONE) // 2^(8*length) - 1
            );
        }

        MutatePacketRuleAction action = new MutatePacketRuleAction.Builder()
                .includeHeader(true)
                .addClause(testedField.name, testValue)
                .enableMutation(false) // not testing mutation in this test
                .build();

        // Create a byte array copy of the message that we store for later
        ByteBuf refBuf = Unpooled.buffer();
        ByteBuf buf = Unpooled.buffer();
        ofMessage.writeTo(buf);
        ofMessage.writeTo(refBuf);

        // Mutate the packet
        Methods.mutatePacketRule(pktStruct, buf, action);

        buf.readerIndex(0);
        refBuf.readerIndex(0);
        byte[] original = new byte[refBuf.readableBytes()];
        byte[] fuzzed = new byte[buf.readableBytes()];
        refBuf.readBytes(original);
        buf.readBytes(fuzzed);

        // First assert that the Openflow Header is unmodified
        BigInteger oldValue = new BigInteger(1, Arrays.copyOfRange(original, testedField.offset, testedField.offset + testedField.length));
        BigInteger newValue = new BigInteger(1, Arrays.copyOfRange(fuzzed  , testedField.offset, testedField.offset + testedField.length));

        System.out.println("Tested field: " + testedField.toString() + " | has mask ?: " + testedField.hasMask);
        if (testedField.hasMask)
        {
            System.out.println("test value: " + testValue.toString() + " (" + testValue.toString(2) + ")");
            System.out.println("mutation effect (unmasked): " + oldValue.toString(2) + " -> " + newValue.toString(2));
            oldValue = oldValue.and(BigInteger.valueOf(testedField.mask)).shiftRight(mtz);
            newValue = newValue.and(BigInteger.valueOf(testedField.mask)).shiftRight(mtz);
            System.out.println("mutation effect (masked): " + oldValue.toString() + " (" + oldValue.toString(2) + ") -> " + newValue.toString() + " (" + newValue.toString(2) + ")");
        }
        else
        {
            newValue = new BigInteger(1, Arrays.copyOfRange(fuzzed  , testedField.offset, testedField.offset + testedField.length));
            System.out.println("expected value: " + testValue.toString());
            System.out.println("mutation effect: " + oldValue + " -> " + newValue);
        }

        // Assert that the new value is equal to the testValue
        Assertions.assertEquals(0, newValue.compareTo(testValue));
    }


    @RepeatedTest(10)
    void mutatePacketRule_ShouldMutateOnlyTheFieldsInTheRule_WhenARuleIsSpecifiedWithValueConditionsAndMutationIsDisabled()
    {
        // Create a new scramble all action
        OFPacketIn ofPacketIn = dummyOFPacketIn();
        PktStruct pktStruct = OFPktStruct.fromOFMessage(ofPacketIn);
        MutatePacketRuleAction.Builder actionBuilder = new MutatePacketRuleAction.Builder()
                .includeHeader(false)
                .enableMutation(false);

        // Get a random field that will be the target of the test and create the action
        LinkedList<Integer> fieldsToFuzz = new LinkedList<>();
        int fieldToFuzzCount = 1 + random.nextInt(pktStruct.size() - 4 - 2); // 1 + (size - headercount - 1) - 1
        int idx;
        for (int i = 0; i < fieldToFuzzCount ; i++ )
        {
            do
            {
                idx = 4 + random.nextInt(pktStruct.size() - 4); // Exclude the header...
            }
            while (fieldsToFuzz.contains(idx));

            fieldsToFuzz.add(idx);
            PktStruct.Field testedField = pktStruct.getByIndex(idx);

            BigInteger testValue;
            if (testedField.hasMask)
            {
                int _maxInt = testedField.mask;
                while ((_maxInt & 1) == 0)
                {
                    _maxInt >>= 1;
                }
                testValue = ByteUtil.randomBigInteger(BigInteger.ZERO, BigInteger.valueOf(_maxInt));
            }
            else
            {
                testValue = ByteUtil.randomBigInteger(
                        BigInteger.ZERO,
                        BigInteger.TWO.pow(8 * testedField.length).subtract(BigInteger.ONE)
                );
            }

            actionBuilder.addClause(testedField.name, testValue);
        }
        // Create the mutation action
        MutatePacketRuleAction action = actionBuilder.build();

        // Create a byte array copy of the message that we store for later
        ByteBuf refBuf = Unpooled.buffer();
        ofPacketIn.writeTo(refBuf);
        ByteBuf buf = refBuf.copy();

        // Create the report object used to count the number of actions performed
        Report report = new Report();
        report.setCurrentAction(action);

        // Mutate the packet
        Methods.mutatePacketRule(pktStruct, buf, action, report);

        // Read the result of the fuzzed message
        buf.readerIndex(0);
        refBuf.readerIndex(0);
        byte[] original = new byte[refBuf.readableBytes()];
        byte[] fuzzed = new byte[buf.readableBytes()];
        refBuf.readBytes(original);
        buf.readBytes(fuzzed);

        // Evaluate the number of difference and if all the fields that needed to be fuzzed have been fuzzed properly
        int mutationOps = report.getMutations().get(action).size();
        int wasNotSupposedToBeFuzzed = 0;
        for (int i=0; i < pktStruct.size(); i++)
        {
            // Extract each field of both the fuzzed original message and the new one
            PktStruct.Field f = pktStruct.getByIndex(i);
            byte[] oldValue = Arrays.copyOfRange(original, f.offset, f.offset + f.length);
            byte[] newValue = Arrays.copyOfRange(fuzzed, f.offset, f.offset + f.length);

            if (f.hasMask)
            {
                int _new = f.mask;
                int mtz = 0;
                while ((_new & 1) == 0)
                {
                    _new >>= 1;
                    mtz++;
                }

                BigInteger oldValueBI = new BigInteger(1, oldValue);
                BigInteger newValueBI = new BigInteger(1, newValue);

                oldValueBI = oldValueBI.and(BigInteger.valueOf(f.mask)).shiftRight(mtz);
                newValueBI = newValueBI.and(BigInteger.valueOf(f.mask)).shiftRight(mtz);

                oldValue = oldValueBI.toByteArray();
                newValue = newValueBI.toByteArray();
            }

            if (!Arrays.equals(newValue, oldValue))
            {
                if (!fieldsToFuzz.contains(i))
                    wasNotSupposedToBeFuzzed++;
            }
        }

        // That the field value has changed and that new value is between the correct range
        Assertions.assertFalse(Arrays.equals(original, fuzzed));
        // It's better to count the mutation operations has there can be some fields that
        // are not fuzzed
        Assertions.assertEquals(fieldToFuzzCount, mutationOps);
        Assertions.assertEquals(0, wasNotSupposedToBeFuzzed);
    }


    @RepeatedTest(100)
    // Test might fail sometimes if it stumble on a field with mask...
    // NOTE: There is a bug in this function with the masks...
    void mutatePacketRule_ShouldMutateTheFieldsInTheRuleAndSomeMore_WhenARuleIsSpecifiedWithValueConditionsAndMutationIsEnabled()
    {
        // Create a new scramble all action
        OFPacketIn ofPacketIn = dummyOFPacketIn();
        PktStruct pktStruct = OFPktStruct.fromOFMessage(ofPacketIn);
        MutatePacketRuleAction.Builder actionBuilder = new MutatePacketRuleAction.Builder()
                .includeHeader(false)
                .enableMutation(true)
                .mutationRateMultiplier(1);

        // Get a random field that will be the target of the test and create the action
        LinkedList<Integer> fieldsToFuzz = new LinkedList<>();
        int fieldToFuzzCount = 1 + random.nextInt(pktStruct.size() - 4 - 2); // 1 + (size - headercount - 1) - 1
        int idx;
        for (int i = 0; i < fieldToFuzzCount ; i++ )
        {
            do
            {
                idx = 4 + random.nextInt(pktStruct.size() - 4); // exclude the headers...
            }
            while (fieldsToFuzz.contains(idx));

            fieldsToFuzz.add(idx);
            PktStruct.Field testedField = pktStruct.getByIndex(idx);

            BigInteger testValue;
            if (testedField.hasMask)
            {
                int _maxInt = testedField.mask;
                while ((_maxInt & 1) == 0)
                {
                    _maxInt >>= 1;
                }
                testValue = ByteUtil.randomBigInteger(BigInteger.ZERO, BigInteger.valueOf(_maxInt));
            }
            else
            {
                testValue = ByteUtil.randomBigInteger(
                        BigInteger.ZERO,
                        BigInteger.TWO.pow(8 * testedField.length).subtract(BigInteger.ONE)
                );
            }

            actionBuilder.addClause(testedField.name, testValue);
        }

        // Create the mutation action
        MutatePacketRuleAction action = actionBuilder.build();

        // Create a byte array copy of the message that we store for later
        ByteBuf refBuf = Unpooled.buffer();
        ofPacketIn.writeTo(refBuf);
        ByteBuf buf = refBuf.copy();

        // Create the report object used to count the number of actions performed
        Report report = new Report();
        report.setCurrentAction(action);

        // Mutate the packet
        Methods.mutatePacketRule(pktStruct, buf, action, report);

        // Read the result of the fuzzed message
        buf.readerIndex(0);
        refBuf.readerIndex(0);
        byte[] original = new byte[refBuf.readableBytes()];
        byte[] fuzzed = new byte[buf.readableBytes()];
        refBuf.readBytes(original);
        buf.readBytes(fuzzed);

        // Evaluate the number of difference and if all the fields that needed to be fuzzed have been fuzzed properly
        ArrayList<Report.Mutation> mutationList = report.getMutations().get(action);
        int mutationOps = mutationList.size();
        int wasInRule = 0;

        // For each mutation, count if it was in the rule or not, regardless of whether or not its value was actually
        // modified
        for (Report.Mutation mutation: mutationList)
        {
            if (fieldsToFuzz.contains(pktStruct.getIndexOfField(mutation.field)))
                wasInRule++;
        }

        // All the fields in the rule must have been mutated
        Assertions.assertEquals(fieldToFuzzCount, wasInRule);
    }

    // ===== ( mutateField Method Tests ) ==============================================================================


    @RepeatedTest(50)
    void mutateField_ShouldMutateOnlyTheCorrectField_WhenNoRangeIsSpecified()
    {
        byte[] dummyPacket = dummyPacket();
        PktStruct dummyStruct = dummyStruct(dummyPacket);

        int indexToMutate = random.nextInt(dummyStruct.size() - 1);
//        dummyStruct.getByIndex(random.nextInt(dummyStruct.size()) - 1).name

        // Generate a packet
        MutateFieldAction action = new MutateFieldAction.Builder()
                .fieldName(dummyStruct.getByIndex(indexToMutate).name)
                .build();

        ByteBuf refBuf = Unpooled.wrappedBuffer(dummyPacket);
        ByteBuf buf = refBuf.copy();

        Methods.mutateField(dummyStruct, buf, action);

        // Read the bytes of the both buffs
        buf.readerIndex(0);
        refBuf.readerIndex(0);
        byte[] original = new byte[refBuf.readableBytes()];
        byte[] fuzzed = new byte[buf.readableBytes()];
        refBuf.readBytes(original);
        buf.readBytes(fuzzed);

        // Check that the field is different
        // Extract each field of both the fuzzed original message and the new one
        for (int i=0; i < dummyStruct.size(); i++)
        {
            PktStruct.Field f = dummyStruct.getByIndex(i);
            byte[] originalValue = Arrays.copyOfRange(original, f.offset, f.offset + f.length);
            byte[] fuzzedValue = Arrays.copyOfRange(fuzzed, f.offset, f.offset + f.length);

            if (indexToMutate == i)
            {
                Assertions.assertFalse(Arrays.equals(originalValue, fuzzedValue));
            }
            else
            {
                Assertions.assertArrayEquals(originalValue, fuzzedValue);
            }
        }
    }

    // ===== ( mutatePacketByte Method Tests ) =========================================================================

    @RepeatedTest(50)// TODO: Extend test to use select a random number of fields and random ranges within the size of the field
    void mutatePacketBytes_ShouldMutateOnlyThePayload_WhenHeaderIsExcluded()
    {
        // Create a new scramble all action
        OFPacketIn ofPacketIn = dummyOFPacketIn();
        PktStruct pktStruct = OFPktStruct.fromOFMessage(ofPacketIn);

        // Get a random field that will be the target of the test and create the action
        PktStruct.Field testedField = pktStruct.getByIndex(random.nextInt(pktStruct.size()));
        MutateBytesAction action = new MutateBytesAction.Builder()
                .includeHeader(false)
                .build();

        // Create a byte array copy of the message that we store for later
        ByteBuf refBuf = Unpooled.buffer();
        ByteBuf buf = Unpooled.buffer();
        ofPacketIn.writeTo(buf);
        ofPacketIn.writeTo(refBuf);

        // Mutate the packet
        Methods.mutateBytes(pktStruct, buf, action);

        buf.readerIndex(0);
        refBuf.readerIndex(0);
        byte[] original = new byte[refBuf.readableBytes()];
        byte[] fuzzed = new byte[buf.readableBytes()];
        refBuf.readBytes(original);
        buf.readBytes(fuzzed);

        // First assert that the Openflow Header is unmodified
        PktStruct.Field f = pktStruct.getByIndex(4);
        byte[] originalValue = Arrays.copyOfRange(original, 0, f.offset);
        byte[] fuzzedValue = Arrays.copyOfRange(fuzzed, 0, f.offset);
        // Assert that all the fields are the same
        Assertions.assertArrayEquals(fuzzedValue, originalValue);

        // Start at the beginning of the packet payload
        int diff = 0;
        for (int i=4; i < pktStruct.size(); i++)
        {
            // Extract each field of both the fuzzed original message and the new one
            f = pktStruct.getByIndex(i);
            originalValue = Arrays.copyOfRange(original, f.offset, f.offset + f.length);
            fuzzedValue = Arrays.copyOfRange(fuzzed, f.offset, f.offset + f.length);

            // Check that the fields is different
            if (!Arrays.equals(fuzzedValue, originalValue))
            {
                diff += 1;
            }
        }
        // Assert that the number of differences is equal to the number of fields in the packet minus the header
        Assertions.assertTrue(diff > 5);
    }

}