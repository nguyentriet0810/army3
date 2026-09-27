// Read-only decompiler inventory of calls to a selected message constructor.
// Usage: -postScript DecompileMessageConstructorCalls.java 180297C50 [timeoutSeconds]
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.LinkedHashMap;
import java.util.Map;

public class DecompileMessageConstructorCalls extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 1) {
            throw new IllegalArgumentException("Pass constructor address and optional timeout");
        }
        int timeout = args.length > 1 ? Integer.parseInt(args[1]) : 8;
        Address query = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Function target = currentProgram.getFunctionManager().getFunctionContaining(query);
        if (target == null) throw new IllegalArgumentException("No target function at " + query);

        Map<Address, Function> owners = new LinkedHashMap<>();
        ReferenceIterator refs = currentProgram.getReferenceManager()
            .getReferencesTo(target.getEntryPoint());
        while (refs.hasNext()) {
            Reference ref = refs.next();
            if (!ref.getReferenceType().isCall()) continue;
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(ref.getFromAddress());
            if (owner != null) owners.put(owner.getEntryPoint(), owner);
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int completed = 0;
        int matchedFunctions = 0;
        int matchedLines = 0;
        try {
            for (Function owner : owners.values()) {
                if (monitor.isCancelled()) break;
                DecompileResults result = decompiler.decompileFunction(owner, timeout, monitor);
                if (!result.decompileCompleted()) {
                    println("OWNER=" + owner.getEntryPoint() + " STATUS=decompile-failed");
                    continue;
                }
                completed++;
                boolean matched = false;
                String[] lines = result.getDecompiledFunction().getC().split("\\R");
                for (String line : lines) {
                    if (!line.contains(target.getName() + "(")) continue;
                    println("OWNER=" + owner.getEntryPoint() + " CALL=" + line.trim());
                    matched = true;
                    matchedLines++;
                }
                if (matched) matchedFunctions++;
            }
        }
        finally {
            decompiler.dispose();
        }
        println("SUMMARY TARGET=" + target.getEntryPoint() + " OWNERS=" + owners.size() +
            " COMPLETED=" + completed + " MATCHED_FUNCTIONS=" + matchedFunctions +
            " MATCHED_LINES=" + matchedLines + " TIMEOUT=" + timeout);
    }
}
