// Read-only decompiler scan for assignments in functions referencing a type-info slot.
// Usage: -postScript InspectStaticAssignments.java 181454520 [timeoutSeconds]
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.LinkedHashMap;
import java.util.Map;

public class InspectStaticAssignments extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            throw new IllegalArgumentException("Pass type-info slot and optional timeout");
        }
        int timeout = args.length > 1 ? Integer.parseInt(args[1]) : 10;
        Address slot = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        String pointer = "DAT_" + args[0].toLowerCase();

        Map<Address, Function> owners = new LinkedHashMap<>();
        ReferenceIterator refs = currentProgram.getReferenceManager().getReferencesTo(slot);
        while (refs.hasNext()) {
            Reference ref = refs.next();
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(ref.getFromAddress());
            if (owner != null) owners.put(owner.getEntryPoint(), owner);
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int completed = 0;
        int assignments = 0;
        try {
            for (Function owner : owners.values()) {
                if (monitor.isCancelled()) break;
                DecompileResults result = decompiler.decompileFunction(owner, timeout, monitor);
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    println("OWNER=" + owner.getEntryPoint() + " STATUS=decompile-failed");
                    continue;
                }
                completed++;
                String[] lines = result.getDecompiledFunction().getC().split("\\R");
                for (int index = 0; index < lines.length; index++) {
                    String line = lines[index];
                    if (!line.contains(pointer) || !line.contains("=")) continue;
                    String trimmed = line.trim();
                    if (trimmed.startsWith("if (") || trimmed.startsWith("while (") ||
                        trimmed.startsWith("return ") || trimmed.contains("==") ||
                        trimmed.contains("!=")) continue;
                    println("OWNER=" + owner.getEntryPoint() + " LINE=" + (index + 1) +
                        " ASSIGN=" + trimmed);
                    assignments++;
                }
            }
        }
        finally {
            decompiler.dispose();
        }
        println("SUMMARY SLOT=" + slot + " OWNERS=" + owners.size() +
            " COMPLETED=" + completed + " ASSIGNMENTS=" + assignments +
            " TIMEOUT=" + timeout);
    }
}
