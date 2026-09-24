// Read-only decode of a bounded region absent from the Ghidra listing.
// Usage: -postScript InspectPseudoInstructions.java 180203B91 50

import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;

public class InspectPseudoInstructions extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException("Pass start address and instruction count");
        }
        int limit = Integer.parseInt(args[1]);
        if (limit < 1 || limit > 100) {
            throw new IllegalArgumentException("Count must be 1..100");
        }
        Address cursor = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        PseudoDisassembler disassembler = new PseudoDisassembler(currentProgram);
        int count = 0;
        while (count < limit && !monitor.isCancelled()) {
            PseudoInstruction instruction;
            try {
                instruction = disassembler.disassemble(cursor);
            } catch (Exception exception) {
                println("STOP=" + cursor + " ERROR=" +
                    exception.getClass().getSimpleName() + ": " +
                    exception.getMessage());
                break;
            }
            if (instruction == null || instruction.getLength() < 1) {
                println("STOP=" + cursor + " ERROR=no instruction");
                break;
            }
            println("INSTRUCTION=" + cursor + " " +
                instruction.toString() + " FLOW=" +
                instruction.getFlowType());
            count++;
            cursor = cursor.add(instruction.getLength());
        }
        println("COUNT=" + count + " NEXT=" + cursor + " LIMIT=" + limit);
    }
}
