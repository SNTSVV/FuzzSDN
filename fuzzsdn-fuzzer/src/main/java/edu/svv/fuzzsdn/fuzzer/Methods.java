package edu.svv.fuzzsdn.fuzzer;

import edu.svv.fuzzsdn.common.utils.ByteBufUtil;
import edu.svv.fuzzsdn.common.utils.ByteUtil;
import edu.svv.fuzzsdn.common.openflow.PktStruct;
import edu.svv.fuzzsdn.common.utils.types.Pair;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.*;
import io.netty.buffer.ByteBuf;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.json.Json;
import javax.json.JsonArrayBuilder;
import javax.json.JsonObjectBuilder;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.math.RoundingMode;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Random;
import java.util.concurrent.ThreadLocalRandom;
import java.util.stream.Collectors;
import java.util.stream.IntStream;

public final class Methods
{
    private static final Logger log = LoggerFactory.getLogger(Methods.class);

    /**
     * {@code fuzzInfo} defaults to {@code null}
     * @see Methods#mutatePacket(PktStruct, ByteBuf, MutatePacketAction, Report)
     */
    public static void mutatePacket(PktStruct pktStruct, ByteBuf buffer, MutatePacketAction action)
    {
        mutatePacket(pktStruct, buffer, action, null);
    }

    /**
     * Mutate a given network byte stream according to a {@link MutatePacketAction} instruction.
     *
     * @param pktStruct The {@link PktStruct} object that holds the information about the packet being mutated
     * @param buffer    The {@link ByteBuf} object that holds the byte information about the packet
     * @param action    The {@link MutatePacketAction} object that holds the instructions about how to mutate the
     *                  incoming packet.
     * @param history   The {@link Report} object to which store the fuzzing context
     */
    public static void mutatePacket(PktStruct pktStruct, ByteBuf buffer, MutatePacketAction action, Report history)
    {
        // Create a list of all the fields index that can be fuzzed and then remove the indexes of the headers if needed
        List<Integer> fieldList = IntStream.range(0, pktStruct.size()).boxed().collect(Collectors.toList());
        if (!action.includesHeader())
        {
            // TODO: Add support for other protocols
            if (action.getTarget() == Action.Target.OF_PACKET)
            {  // Remove the fields associated with an openflow header
                fieldList = fieldList.subList(4, fieldList.size());
            }
            else
            {
                throw new UnsupportedOperationException("mutatePacket method does not support target of type \"" +
                        action.getTarget().name + "\"");
            }
        }

        // Determine the number of fields to mutate
        int fieldsToMutate = ThreadLocalRandom.current().nextInt(1, fieldList.size());
        randomFieldMutation(pktStruct, buffer, fieldList, fieldsToMutate, history);
    }

    /**
     * {@code fuzzHistory} defaults to {@code null}
     * @see Methods#mutatePacketRule(PktStruct, ByteBuf, MutatePacketRuleAction, Report)
     */
    public static void mutatePacketRule(PktStruct pktStruct, ByteBuf buffer, MutatePacketRuleAction action)
    {
        mutatePacketRule(pktStruct, buffer, action, null);
    }

    /**
     * Mutate a given network byte stream according to a {@link MutatePacketAction} instruction.
     *
     * @param pktStruct The {@link PktStruct} object that holds the information about the packet being mutated
     * @param buffer    The {@link ByteBuf} object that holds the byte information about the packet
     * @param action    The {@link MutatePacketRuleAction} object that holds the instructions about how to mutate the
     *                  incoming packet.
     * @param report   The {@link Report} object to which store the fuzzing context
     */
    public static void mutatePacketRule(PktStruct pktStruct, ByteBuf buffer, MutatePacketRuleAction action, Report report)
    {
        // 1. Create a list of all the fields index that can be fuzzed and then remove the indexes of the headers if needed
        List<Integer> fieldList = IntStream.range(0, pktStruct.size()).boxed().collect(Collectors.toList());
        if (!action.isHeaderIncluded())
        {
            log.trace("Ignoring header");
            // TODO: Add support for other protocols
            if (action.getTarget() == Action.Target.OF_PACKET)
            {  // Remove the fields associated with an openflow header
                fieldList = fieldList.subList(4, fieldList.size());
            }
            else
            {
                throw new UnsupportedOperationException("mutatePacket method does not support target of type \"" +
                        action.getTarget().name + "\"");
            }
        }

        // 2. Create an ...
        JsonArrayBuilder clauseInfoJArr = Json.createArrayBuilder();

        // 3. Mutate the fields that are part of the condition
        Collection<MutatePacketRuleAction.Clause> clauses = action.getClauses();
        for (MutatePacketRuleAction.Clause clause : clauses)
        {
            log.trace("Handling " + clause.toString() + "...");
            // 3.1 If the field in the clause is present in the packet...
            if (pktStruct.hasField(clause.getField()))
            {

                // 3.2 Get the field and its index
                PktStruct.Field fieldToMutate = pktStruct.getByName(clause.getField());
                int index = pktStruct.getIndexOfField(clause.getField());
                log.trace("Field to mutate:" + fieldToMutate.toString() + "(" + index + ")");

                // 3.3 Remove the field bound to the condition from the list of fields "not fuzzed" fields and declare
                // array of "bytes to write"
                fieldList.removeIf(f -> f.equals(index));
                byte[] bytesToWrite;
                byte[] oldFieldValue = ByteBufUtil.readBytes(buffer, fieldToMutate.offset, fieldToMutate.length, true);

                // 3.5a If the clause is range...
                if (clause.isRanged() && clause.getRange() != null)
                {
                    // 3.5a.1 Calculate the max value of the field
                    BigInteger maxFieldValue;
                    if (fieldToMutate.hasMask)
                    {
                        // Get the maximum size of the number to generate from the mask.
                        // The size is determined by the consecutive 1s in the bit string
                        int _maxInt = fieldToMutate.mask;
                        while ((_maxInt & 1) == 0)
                        {
                            _maxInt >>= 1;
                        }
                        maxFieldValue = BigInteger.valueOf(_maxInt);
                    }
                    else
                    {
                        maxFieldValue = new BigInteger("2").pow(fieldToMutate.length * 8).subtract(BigInteger.ONE);
                    }

                    // 3.5a.2 Get a new value between the min and the max
                    BigInteger newValue;
                    Collection<Pair<BigInteger>> ranges = clause.getRange();
                    if (ranges != null && !ranges.isEmpty())
                    {
                        BigInteger valueCount = BigInteger.ZERO;
                        for (Pair<BigInteger> r : ranges)
                            // valueCount = valueCount + abs(r.right - r.left) + 1
                            valueCount = valueCount.add(r.right.subtract(r.left).abs().add(BigInteger.ONE));

                        // Choose which range to select from
                        BigDecimal previous = BigDecimal.ZERO;
                        BigDecimal next;
                        double rnd1 = ThreadLocalRandom.current().nextDouble();
                        Pair<BigInteger> sRange = ranges.iterator().next();
                        for (Pair<BigInteger> r : ranges)
                        {
                            BigDecimal right = new BigDecimal(r.right);
                            BigDecimal left = new BigDecimal(r.left);

                            // next = previous + (abs(right - left) + 1)/valueCount
                            next = previous
                                    .add(right
                                            .subtract(left).abs()
                                            .add(BigDecimal.ONE)
                                            .divide(new BigDecimal(valueCount), RoundingMode.UNNECESSARY)
                                    );

                            // if (rnd1 < next)
                            if (new BigDecimal(rnd1).compareTo(next) < 0)
                            {
                                sRange = r;
                                break;
                            }
                            else
                            {
                                previous = next;
                            }
                        }

                        // Select a random number within the range and the min and max value of a field
                        newValue = ByteUtil.randomBigInteger(
                                sRange.left.max(BigInteger.ZERO),
                                sRange.right.min(maxFieldValue)
                        );
                    }
                    else
                    {
                        newValue = ByteUtil.randomBigInteger(BigInteger.ZERO, maxFieldValue);
                    }

                    // 3.5a.3 Convert the number to write into bytes
                    log.trace("New value for field to mutate: " + newValue);

                    // 3.5a.4 Assign the new byte to the field
                    if (fieldToMutate.hasMask)
                    {
                        // Get the old field value
                        byte[] _oldFieldValue = ByteBufUtil.readBytes(buffer, fieldToMutate.offset, fieldToMutate.length, true);

                        BigInteger _old = new BigInteger(1, _oldFieldValue);
                        BigInteger _mask = BigInteger.valueOf(fieldToMutate.mask);

                        // get the number of trailing zeros in the mask
                        int mask_copy = fieldToMutate.mask;
                        int mtz = 0;
                        while ((mask_copy & 1) == 0)
                        {
                            mask_copy >>= 1;
                            mtz++;
                        }
                        // BigInteger _new = _old.andNot(_mask).or(clause.getValue().shiftLeft(mtz));
                        BigInteger _new = _old.andNot(_mask).or(newValue.shiftLeft(mtz));
                        bytesToWrite = ByteUtil.bigIntegerToBytes(_new, fieldToMutate.length);
                    }
                    else
                    {
                        bytesToWrite = ByteUtil.bigIntegerToBytes(newValue, fieldToMutate.length);
                    }
                }
                // 3.5b If the clause is a single value
                else if (!clause.isRanged() && clause.getValue() != null)
                {
                    // 3.5b.1a If the field has a mask, a mask must be applied
                    if (fieldToMutate.hasMask)
                    {
                        // Get the old field value
                        byte[] _oldFieldValue = new byte[fieldToMutate.length];
                        buffer.readerIndex(fieldToMutate.offset);
                        buffer.readBytes(_oldFieldValue);

                        BigInteger _old = new BigInteger(1, _oldFieldValue);
                        BigInteger _mask = BigInteger.valueOf(fieldToMutate.mask);
                        // Get the number of trailing zeros in the field
                        int _maxInt = fieldToMutate.mask;
                        int mtz = 0;
                        while ((_maxInt & 1) == 0)
                        {
                            _maxInt >>= 1;
                            mtz++;
                        }
                        BigInteger _new = _old.andNot(_mask).or(clause.getValue().shiftLeft(mtz))
                                .max(BigInteger.ZERO)
                                .min(BigInteger.TWO.pow(fieldToMutate.length * 8).subtract(BigInteger.ONE));
                        bytesToWrite = ByteUtil.bigIntegerToBytes(_new, fieldToMutate.length);
                    }
                    // 3.5b.1b Otherwise, simply assign a new value between the the min and max
                    else
                    {
                        BigInteger _new = clause.getValue()
                                .max(BigInteger.ZERO)
                                .min(BigInteger.TWO.pow(fieldToMutate.length * 8).subtract(BigInteger.ONE));
                        bytesToWrite = ByteUtil.bigIntegerToBytes(_new, fieldToMutate.length);
                    }
                }
                else
                {
                    log.warn("Clause \"" + clause + "\" as an empty range/value. Ignoring it...");
                    continue;
                }

                // 3.6 Write at the bytes at the field location
                ByteBufUtil.writeBytes(buffer, bytesToWrite, fieldToMutate.offset);

                // 3.7 Add the mutation info to the fuzz report
                if (report != null)
                    report.addMutation(
                            Report.MutationType.RULE_BASED_MUTATION,
                            clause.getField(),
                            new BigInteger(1, oldFieldValue),
                            new BigInteger(1, bytesToWrite)
                    );
            }
            // If there is no clause, just do nothing
        }

        // 4. Randomly mutate the rest of the fields if the option is enabled
        if (action.isMutationEnabled() && fieldList.size() > 0)
        {
            double mutationRate = action.getMutationRateMultiplier() / (double) fieldList.size();
            uniformFieldMutation(pktStruct, buffer, fieldList, mutationRate, report);
        }
    }

    /**
     * {@code fuzzHistory} defaults to {@code null}
     * @see Methods#mutatePacketRule(PktStruct, ByteBuf, MutatePacketRuleAction, Report)
     */
    public static void mutateField(PktStruct pktStruct, ByteBuf buffer, MutateFieldAction action)
    {
        mutateField(pktStruct, buffer, action, null);
    }

    /**
     * Mutate a given network byte stream according to a {@link MutateFieldAction} instruction.
     *
     * @param pktStruct The {@link PktStruct} object that holds the information about the packet being mutated
     * @param buffer    The {@link ByteBuf} object that holds the byte information about the packet
     * @param action    The {@link MutateFieldAction} object that holds the instructions about how to mutate the
     *                  incoming packet.
     */
    public static void mutateField(PktStruct pktStruct, ByteBuf buffer, MutateFieldAction action, Report report)
    {
        PktStruct.Field fieldToMutate;
        if (pktStruct.hasField(action.getFieldName()))
        {
            fieldToMutate = pktStruct.getByName(action.getFieldName());
        }
        else
            throw new IllegalArgumentException("Field \"" + action.getFieldName() + "\" is not part of this message");

        // Calculate the max value of the field
        BigInteger maxFieldValue = new BigInteger("2").pow(fieldToMutate.length*8).subtract(BigInteger.ONE);
        BigInteger numberToWrite;
        Collection<Pair<BigInteger>> ranges = action.getRanges();
        if (ranges != null)
        {
            if (!ranges.isEmpty())
            {
                BigInteger valueCount = BigInteger.ZERO;
                for (Pair<BigInteger> r : ranges)
                    // valueCount = valueCount + abs(r.right - r.left) + 1
                    valueCount = valueCount.add(r.right.subtract(r.left).abs().add(BigInteger.ONE));

                // Choose which range to select from
                BigDecimal previous = BigDecimal.ZERO;
                BigDecimal next;
                double rnd1 = ThreadLocalRandom.current().nextDouble();
                Pair<BigInteger> sRange = ranges.iterator().next();
                for (Pair<BigInteger> r : ranges)
                {
                    BigDecimal right = new BigDecimal(r.right);
                    BigDecimal left = new BigDecimal(r.left);

                    // next = previous + (abs(right - left) + 1)/valueCount
                    next = previous
                            .add(right
                                    .subtract(left).abs()
                                    .add(BigDecimal.ONE)
                                    .divide(new BigDecimal(valueCount),RoundingMode.UNNECESSARY)
                            );

                    if (new BigDecimal(rnd1).compareTo(next) < 0)
                    {
                        sRange = r;
                        break;
                    }
                    else
                    {
                        previous = next;
                    }
                }

                // Select a random number within the range and the min and max value of a field
                numberToWrite = ByteUtil.randomBigInteger(
                        sRange.left.max(BigInteger.ZERO),
                        sRange.right.min(maxFieldValue)
                );
            }
            else
            {
                numberToWrite = ByteUtil.randomBigInteger(BigInteger.ZERO, maxFieldValue);
            }
        }
        else
        {
            numberToWrite = ByteUtil.randomBigInteger(BigInteger.ZERO, maxFieldValue);
        }

        // Convert the number to write into bytes
        byte[] bytesToWrite = ByteUtil.bigIntegerToBytes(numberToWrite, fieldToMutate.length);

        // Write at the bytes at the field location
        ByteBufUtil.writeBytes(buffer, bytesToWrite, fieldToMutate.offset);
    }

    /**
     * Mutate a given network byte stream according to a {@link MutateBytesAction} instruction.
     *
     * @param pktStruct The {@link PktStruct} object that holds the information about the packet being mutated
     * @param buffer    The {@link ByteBuf} object that holds the byte information about the packet
     * @param action    The {@link MutatePacketRuleAction} object that holds the instructions about how to mutate the
     *                  incoming packet.
     */
    public static void mutateBytes(PktStruct pktStruct, ByteBuf buffer, MutateBytesAction action)
    {
        // 1. Setup the offset if the header must be included or not
        Random random = new Random();
        int startingOffset = 0;
        if (!action.isHeaderIncluded())
        {
            log.trace("Ignoring header");
            // TODO: Add support for other protocols
            if (action.getTarget() == Action.Target.OF_PACKET)
            {
                // Remove the fields associated with an openflow header
                startingOffset = 8;
            }
            else
            {
                throw new UnsupportedOperationException("mutateByte method does not support target of type \"" +
                        action.getTarget().name + "\"");
            }
        }

        byte[] message = ByteBufUtil.readAllBytes(buffer, true);
        byte[] crafted = new byte[message.length - startingOffset];

        System.arraycopy(message, startingOffset, crafted, 0, message.length - startingOffset);
        random.nextBytes(crafted);
        System.arraycopy(crafted, 0, message, startingOffset, message.length - startingOffset);

        // 2. Write at the bytes at the field location
        ByteBufUtil.writeBytes(buffer, message, 0);

    }


    // ===== ( Helper Methods ) ========================================================================================

    /**
     * Helper method that mutate a random number of fields within a packet
     *
     * @param pktStruct     The {@link PktStruct} object that holds the information about the packet being mutated.
     * @param buffer        The {@link ByteBuf} object that holds the byte information about the packet.
     * @param fieldList     The {@code List<Integer>} of field indices that can be mutated.
     * @param mutationCount The {@code int} number of fields to mutate.
     * @param report        The {@link Report} object to which the information should be added.
     */
    private static void randomFieldMutation(PktStruct pktStruct, ByteBuf buffer, List<Integer> fieldList, int mutationCount, Report report)
    {
        int idx;
        for (int i = 0 ; i < mutationCount ; i++)
        {
            // Choose the index of the field to fuzz
            int randomFieldIndex = ThreadLocalRandom.current().nextInt(fieldList.size());
            idx = fieldList.get(randomFieldIndex);
            PktStruct.Field fieldToMutate = pktStruct.getByIndex(idx);
            fieldList.remove(randomFieldIndex);

            // Issue log message
            log.trace("Field to mutate: " + fieldToMutate.toString());

            // Mutate the selected field
            byte[] oldFieldValue = ByteBufUtil.readBytes(buffer, fieldToMutate.offset, fieldToMutate.length, true);
            byte[] newFieldValue = new byte[fieldToMutate.length];

            // If there is mask to the field
            if (fieldToMutate.hasMask)
            {
                BigInteger _oldVal  = new BigInteger(1, oldFieldValue);
                BigInteger _mask    = BigInteger.valueOf(fieldToMutate.mask);
                int _maxInt = fieldToMutate.mask;  // Get the maximum size of the number to generate
                while ((_maxInt & 1) == 0)
                    _maxInt = _maxInt >> 1;
                BigInteger _max = BigInteger.valueOf(_maxInt);

                // Calculate the new val
                BigInteger _newVal = ByteUtil.randomBigInteger(BigInteger.ZERO, _max);
                newFieldValue = _oldVal.andNot(_mask).or(_newVal).toByteArray();
            }
            else
            {
                // Avoid generating the number again. There is only a 1/(2^(8*field.size)) possibility that it happens
                // but it is still a source of error if it isn't checked for
                do
                {
                    ThreadLocalRandom.current().nextBytes(newFieldValue);
                } while (Arrays.equals(newFieldValue, oldFieldValue));
            }

            // Write the new bytes to the buffer
            ByteBufUtil.writeBytes(buffer, newFieldValue, fieldToMutate.offset);

            // Register the action to the report
            if (report != null)
                report.addMutation(
                        Report.MutationType.RANDOM_MUTATION,
                        fieldToMutate.name,
                        new BigInteger(1, oldFieldValue),
                        new BigInteger(1, newFieldValue)
                );

            // Issue a log message
            log.trace("New field value: " +
                    new BigInteger(1, oldFieldValue).toString() + " -> " +
                    new BigInteger(1, newFieldValue).toString());
        }
    }

    /**
     * Helper method that mutate a random number of fields within a packet
     *
     * @param pktStruct     The {@link PktStruct} object that holds the information about the packet being mutated.
     * @param buffer        The {@link ByteBuf} object that holds the byte information about the packet.
     * @param fieldList     The {@code List<Integer>} of field indices that can be mutated.
     * @param mutationRate  The {@code double} rate to which fields should be mutated.
     * @param report        The {@link Report} object to which the information should be added.
     */
    private static void uniformFieldMutation(PktStruct pktStruct, ByteBuf buffer, List<Integer> fieldList, double mutationRate, Report report)
    {
        for (int idx : fieldList)
        {
            // Determine if the field should be mutated
            if (ThreadLocalRandom.current().nextDouble() <= mutationRate)
            {
                // Get the field to fuzz
                PktStruct.Field fieldToMutate = pktStruct.getByIndex(idx);
                log.trace("Field to mutate: " + fieldToMutate.toString());

                // Mutate the selected field
                byte[] oldFieldValue = ByteBufUtil.readBytes(buffer, fieldToMutate.offset, fieldToMutate.length, true);
                byte[] newFieldValue = new byte[fieldToMutate.length];

                // Register the information
                JsonObjectBuilder fieldMutationInfo = Json.createObjectBuilder();

                // If there is mask to the field
                if (fieldToMutate.hasMask)
                {
                    BigInteger _oldVal = new BigInteger(1, oldFieldValue);
                    BigInteger _mask = BigInteger.valueOf(fieldToMutate.mask);
                    int _maxInt = fieldToMutate.mask;  // Get the maximum size of the number to generate
                    while ((_maxInt & 1) == 0)
                        _maxInt = _maxInt >> 1;
                    BigInteger _max = BigInteger.valueOf(_maxInt);

                    // Calculate the new val
                    BigInteger _newVal = ByteUtil.randomBigInteger(BigInteger.ZERO, _max);
                    newFieldValue = _oldVal.andNot(_mask).or(_newVal).toByteArray();
                }
                else
                {
                    // Avoid generating the number again. There is only a 1/(2^(8*field.size)) possibility that it happens
                    // but it is still a source of error if it isn't checked for
                    do
                    {
                        ThreadLocalRandom.current().nextBytes(newFieldValue);
                    } while (Arrays.equals(newFieldValue, oldFieldValue));
                }

                // Write to the buffer
                ByteBufUtil.writeBytes(buffer, newFieldValue, fieldToMutate.offset);

                // BUG: If there is a mask, we register in the report the value of the unmasked field.
                //      To be fixed at some point.
                // Register the mutation to the fuzz report
                if (report != null)
                    report.addMutation(
                            Report.MutationType.UNIFORM_MUTATION,
                            fieldToMutate.name,
                            new BigInteger(1, oldFieldValue),
                            new BigInteger(1, newFieldValue)
                    );

                // logging
                log.trace("New field value: " +
                        new BigInteger(1, oldFieldValue).toString() + " -> " +
                        new BigInteger(1, newFieldValue).toString());
            }
        }
    }
}
