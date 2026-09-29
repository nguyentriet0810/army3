// Read-only decompiler scan for virtual calls in functions referencing a type-info slot.
// Usage: -postScript FindTypeVirtualCalls.java TYPE_INFO_SLOT VTABLE_OFFSET [timeoutSeconds]
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

public class FindTypeVirtualCalls extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException(
                "Pass type-info slot, virtual-table offset and optional timeout");
        }
        int timeout = args.length > 2 ? Integer.parseInt(args[2]) : 15;
        Address slot = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        String needle = "+ 0x" + args[1].toLowerCase(Locale.ROOT);

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
                    if (!lines[index].toLowerCase(Locale.ROOT).contains(needle)) continue;
                    println("MATCH OWNER=" + owner.getEntryPoint() + " NAME=" + owner.getName() +
                        " LINE=" + (index + 1));
                    for (int line = Math.max(0, index - 4);
                         line <= Math.min(lines.length - 1, index + 4); line++) {
                        println(String.format("%04d: %s", line + 1, lines[line]));
                    }
                    println("END_MATCH");
                    matches++;
                }
            }
        }
        finally {
            decompiler.dispose();
        }
        println("SUMMARY SLOT=" + slot + " VTABLE=0x" + args[1] +
            " OWNERS=" + owners.size() + " COMPLETED=" + completed +
            " MATCHES=" + matches + " TIMEOUT=" + timeout);
    }
}
