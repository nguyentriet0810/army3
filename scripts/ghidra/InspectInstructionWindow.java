// Read-only listing of a bounded disassembly window in an existing project.
// Usage: -postScript InspectInstructionWindow.java 1801FE720 1801FE790

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;

public class InspectInstructionWindow extends GhidraScript {
    private static final int MAX_INSTRUCTIONS = 120;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException("Pass start and end hex addresses");
        }
        Address start = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Address end = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[1]);
        if (start.compareTo(end) > 0) {
            throw new IllegalArgumentException("Start must not exceed end");
        }
        InstructionIterator iterator = currentProgram.getListing()
            .getInstructions(start, true);
        int count = 0;
        while (iterator.hasNext() && !monitor.isCancelled() &&
                count < MAX_INSTRUCTIONS) {
            Instruction instruction = iterator.next();
            if (instruction.getAddress().compareTo(end) > 0) {
                break;
            }
            println("INSTRUCTION=" + instruction.getAddress() + " " +
                instruction.toString());
            count++;
        }
        println("COUNT=" + count + " LIMIT=" + MAX_INSTRUCTIONS);
    }
}
