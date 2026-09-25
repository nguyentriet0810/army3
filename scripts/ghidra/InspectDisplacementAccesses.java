// Read-only search for selected hexadecimal displacements inside native functions.
// Usage: -postScript InspectDisplacementAccesses.java 1804098B0 58 60
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.util.HashSet;

public class InspectDisplacementAccesses extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException("Pass function address and one or more hex displacements");
        }
        Address query = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Function function = currentProgram.getFunctionManager().getFunctionContaining(query);
        println("QUERY=" + query + " FUNCTION=" +
            (function == null ? "<none>" : function.getName()));
        if (function == null) return;

        HashSet<String> needles = new HashSet<>();
        for (int index = 1; index < args.length; index++) {
            String value = args[index].toLowerCase().replaceFirst("^0x", "");
            needles.add("+ 0x" + value + "]");
            needles.add("- 0x" + value + "]");
        }

        int matches = 0;
        InstructionIterator instructions = currentProgram.getListing()
            .getInstructions(function.getBody(), true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            String text = instruction.toString().toLowerCase();
            boolean matched = false;
            for (String needle : needles) {
                if (text.contains(needle)) {
                    matched = true;
                    break;
                }
            }
            if (!matched) continue;
            println("ACCESS=" + instruction.getAddress() + " " + instruction.toString());
            matches++;
        }
        println("ENTRY=" + function.getEntryPoint() + " BODY=" +
            function.getBody().getNumAddresses() + " MATCHES=" + matches);
    }
}
