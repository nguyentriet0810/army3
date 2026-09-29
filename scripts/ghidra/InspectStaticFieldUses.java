// Read-only decompiler scan for a specific static-field use.
// Usage: -postScript InspectStaticFieldUses.java 181454620 155 [timeoutSeconds] [contextLines]
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.LinkedHashMap;
import java.util.Locale;
import java.util.Map;

public class InspectStaticFieldUses extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Pass type-info slot, field offset, optional timeout and context line count");
        }
        int timeout = args.length > 2 ? Integer.parseInt(args[2]) : 10;
        int context = args.length > 3 ? Integer.parseInt(args[3]) : 3;
        Address slot = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        String pointer = "dat_" + args[0].toLowerCase(Locale.ROOT);
        String offset = "+ 0x" + args[1].toLowerCase(Locale.ROOT);

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
        int matches = 0;
        try {
            for (Function owner : owners.values()) {
                if (monitor.isCancelled()) break;
                DecompileResults result = decompiler.decompileFunction(owner, timeout, monitor);
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    continue;
                }
                completed++;
                String[] lines = result.getDecompiledFunction().getC().split("\\R");
                for (int index = 0; index < lines.length; index++) {
                    String lower = lines[index].toLowerCase(Locale.ROOT);
                    if (!lower.contains(offset)) continue;
                    int start = Math.max(0, index - context);
                    int end = Math.min(lines.length - 1, index + context);
                    StringBuilder window = new StringBuilder();
                    boolean hasPointer = false;
                    for (int line = start; line <= end; line++) {
                        String candidate = lines[line];
                        if (candidate.toLowerCase(Locale.ROOT).contains(pointer)) {
                            hasPointer = true;
                        }
                        window.append(String.format("%04d: %s%n", line + 1, candidate));
                    }
                    if (!hasPointer) continue;
                    println("MATCH OWNER=" + owner.getEntryPoint() + " NAME=" + owner.getName() +
                        " LINE=" + (index + 1));
                    print(window.toString());
                    println("END_MATCH");
                    matches++;
                }
            }
        }
        finally {
            decompiler.dispose();
        }
        println("SUMMARY SLOT=" + slot + " FIELD=0x" + args[1] +
            " OWNERS=" + owners.size() + " COMPLETED=" + completed +
            " MATCHES=" + matches + " TIMEOUT=" + timeout);
    }
}
