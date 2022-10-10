package edu.svv.fuzzsdn.fuzzer.instructions;

import edu.svv.fuzzsdn.fuzzer.Fuzzer;
import edu.svv.fuzzsdn.fuzzer.instructions.actions.Action;
import edu.svv.fuzzsdn.fuzzer.instructions.criteria.Criterion;
import edu.svv.fuzzsdn.common.exceptions.ParsingException;
import org.projectfloodlight.openflow.protocol.OFMessage;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.json.*;
import java.io.FileReader;
import java.util.Collection;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;

/**
 * Class holding a set of {@link Instruction}.
 * The InstructionSet aggregates the instructions that the {@link Fuzzer} should
 * execute whenever it receives a message. The class takes care of dispatching the {@link Action} to be performed on an
 * {@link OFMessage} that matches all the {@link Criterion} of an
 * instruction.
 *
 * The class also handles the discarding of the Instructions that have expired.
 */
public class InstructionSet
{
    // ===== ( Members ) ===============================================================================================

    // Instruction set
    private final Set<Instruction> mInstructionSet;

    // Members
    private boolean mAutoFilter;  // auto-filter enable

    // ===== ( Constructor ) ===========================================================================================

    public InstructionSet(Instruction... instructions)
    {
        // HashSet so we ensure that all instructions are unique.
        this.mInstructionSet = new HashSet<>();
        this.mAutoFilter = true;  // Set to true by default

        // Add all instructions
        if (instructions.length > 0)
        {
            Collections.addAll(mInstructionSet, instructions);
        }
    }

    // ===== ( Getters ) ===============================================================================================

    // ===== ( Setters ) ===============================================================================================

    /**
     * Adds an instruction to the InstructionSet object
     *
     * @param instruction the {@link Instruction}  to be stored
     * @return this InstructionSet object
     */
    public InstructionSet addInstruction(Instruction instruction)
    {
        if (!mInstructionSet.contains(instruction))
            this.mInstructionSet.add(instruction);
        return this;
    }

    /**
     * Enable/Disable the auto-filtering of expired {@link Instruction}
     * @param enable true to enable the auto-filter functionality
     * @return this InstructionSet object
     */
    public InstructionSet autoFilter(boolean enable)
    {
        this.mAutoFilter = enable;
        return this;
    }

    // ===== ( Methods ) ===============================================================================================

    public Collection<Instruction> getInstructions()
    {
        return this.mInstructionSet;
    }

    /**
     * Get the set of {@link Action} to be applied to the OpenFlow message.
     *
     * @param msg The {@link OFMessage} to get the fuzzing action for.
     * @return a {@link Collection} of Actions or {@code null} if no actions are applicable
     */
    public Collection<Action> getActionsFor(OFMessage msg)
    {
        // Using an HashSet so there are only unique actions
        Set<Action> actionSet = new HashSet<>();

        for (Instruction instruction : mInstructionSet)
        {
            // If the message has not expired (this has to be tested before)
            // and the instruction is matching...
            if (!instruction.hasExpired())
            {
                if (instruction.isMatching(msg))
                {
                    // for each actions
                    for (Action action : instruction.getActions())
                    {
                        if (action.canBeAppliedTo(msg))
                            actionSet.add(action);
                    }
                }
            }
        }

        // Filter out the expired elements
        if (this.mAutoFilter)
            filterExpiredInstruction();

        if (actionSet.isEmpty())
            return null;
        else
            return actionSet;
    }

    /**
     * Removes all of the {@link Instruction} of this Instruction that are expired.
     * @return true if any elements were removed
     */
    public boolean filterExpiredInstruction()
    {
        return mInstructionSet.removeIf(Instruction::hasExpired);
    }

    // ===== ( Reader ) ================================================================================================

    public static final Reader READER = new Reader();
    public static final class Reader
    {
        private static final Logger log = LoggerFactory.getLogger(Reader.class);

        // ===== ( Public Methods ) ========================================================================================

        /**
         * Decode the instructions from a JSON file
         * @param path : the string path to the file containing the instrutioncs
         * @return     : an {@link InstructionSet} containing the decoded instructions. null is returned if the instructions
         *               couldn't be decoded
         */
        public static InstructionSet readJSONFile(String path)
        {
            JsonReader reader = null;
            InstructionSet instructionSet = null;

            try
            {
                // Load the json file
                reader = Json.createReader(new FileReader(path));
                JsonObject jsonObj = reader.readObject();

                // Process the json object file
                instructionSet = readJSON(jsonObj);
            }
            catch (Exception ioe)
            {
                log.error("An exception occurred while reading the instruction file \"{}\"", path, ioe);
            }
            finally
            {
                if (reader != null)
                    reader.close();
            }

            return instructionSet;
        }

        // ===== (Private Methods) =========================================================================================

        /**
         * Process a JsonObject containing a set of instructions.
         *
         * @param jsonObj : the {@link JsonObject} containing the instructions.
         * @return an {@link InstructionSet} containing the parsed instructions. Returns null if no instructions are parsed
         */
        public static InstructionSet readJSON(JsonObject jsonObj) throws ParsingException
        {
            InstructionSet output = new InstructionSet();
            Instruction instruction;

            // First parse the criteria if they exists
            if (jsonObj.containsKey("instructions")) // TODO: find a away to not have to declare an "instruction" object
            {
                JsonArray instructionArray = jsonObj.getJsonArray("instructions");
                // Each object of the "instructions" array is an instruction in itself
                for (JsonValue jVal : instructionArray)
                {
                    // Cast to json object
                    JsonObject jObj = ((JsonObject) jVal);
                    output.addInstruction(Instruction.READER.readJSON(jObj));
                }
            }
            else
            {
                throw new IllegalArgumentException("No \"instructions\" array found in the JSON object");
            }

            return output;
        }
    }

    // ===== ( Object Overrides ) ======================================================================================

    /**
     * String representation of this Pair. See {@link Object#toString}
     */
    public String toString()
    {
        StringBuilder sb = new StringBuilder(InstructionSet.class.getSimpleName() + "@" + hashCode());

        boolean first = true;
        sb.append(":[");
        for (Instruction instruction : mInstructionSet)
        {
            if (first)
                first = false;
            else
                sb.append(", ");
            sb.append(instruction.toString());
        }
        sb.append("]");

        return sb.toString();
    }
}
