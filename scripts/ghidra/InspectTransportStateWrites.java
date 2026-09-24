// Read-only scan of direct assignments to the transport codec state.
// Usage: -postScript InspectTransportStateWrites.java 1814545B8

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Pattern;

public class InspectTransportStateWrites extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException("Pass one hexadecimal class-pointer address");
        }
        Address address = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Map<Address, Function> functions = new LinkedHashMap<>();
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(address);
        while (references.hasNext() && !monitor.isCancelled()) {
            Reference reference = references.next();
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            if (function != null) {
                functions.put(function.getEntryPoint(), function);
            }
        }
        println("FUNCTIONS=" + functions.size());
        String pointer = "DAT_" + args[0].toLowerCase();
        Pattern assignment = Pattern.compile("\\+ 0x(60|68|70|71|72)\\)\\s*=(?!=)");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int completed = 0;
        int matches = 0;
        try {
            for (Function function : functions.values()) {
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults result = decompiler.decompileFunction(function, 12, monitor);
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    println("INCOMPLETE=" + function.getEntryPoint());
                    continue;
                }
                completed++;
                String[] lines = result.getDecompiledFunction().getC().split("\\R");
                for (int i = 0; i < lines.length; i++) {
                    if (lines[i].contains(pointer) && assignment.matcher(lines[i]).find()) {
                        println("ASSIGNMENT=" + function.getEntryPoint() +
                            " LINE=" + (i + 1) + " " + lines[i].trim());
                        for (int j = i + 1; j < Math.min(lines.length, i + 3); j++) {
                            println("CONT=" + lines[j].trim());
                        }
                        matches++;
                    }
                }
            }
        } finally {
            decompiler.dispose();
        }
        println("DECOMPILED=" + completed + " MATCHES=" + matches);
    }
}
