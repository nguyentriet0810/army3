// Read-only search for a static-field displacement in functions that reference
// a selected IL2CPP type-info slot.
// Usage: -postScript FindStaticFieldAccesses.java 1814545E8 188

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.LinkedHashMap;
import java.util.Map;

public class FindStaticFieldAccesses extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException(
                "Pass a type-info slot address and a hexadecimal field displacement");
        }

        Address slot = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        String displacement = args[1].toLowerCase().replaceFirst("^0x", "");
        String positiveNeedle = "+ 0x" + displacement + "]";
        String negativeNeedle = "- 0x" + displacement + "]";

        Map<Address, Function> owners = new LinkedHashMap<>();
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(slot);
        while (references.hasNext() && !monitor.isCancelled()) {
            Reference reference = references.next();
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            if (owner != null) {
                owners.put(owner.getEntryPoint(), owner);
            }
        }

        int matchingFunctions = 0;
        int matchingInstructions = 0;
        for (Function owner : owners.values()) {
            boolean announced = false;
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(owner.getBody(), true);
            while (instructions.hasNext() && !monitor.isCancelled()) {
                Instruction instruction = instructions.next();
                String text = instruction.toString().toLowerCase();
                if (!text.contains(positiveNeedle) &&
                    !text.contains(negativeNeedle)) {
                    continue;
                }
                if (!announced) {
                    println("FUNCTION=" + owner.getEntryPoint() + " NAME=" +
                        owner.getName() + " BODY=" + owner.getBody().getNumAddresses());
                    announced = true;
                    matchingFunctions++;
                }
                println("ACCESS=" + instruction.getAddress() + " " +
                    instruction.toString());
                matchingInstructions++;
            }
        }

        println("TYPE_INFO_SLOT=" + slot + " REFERENCING_FUNCTIONS=" +
            owners.size() + " MATCHING_FUNCTIONS=" + matchingFunctions +
            " MATCHING_INSTRUCTIONS=" + matchingInstructions);
    }
}
