// Read-only summary of constructor and selected payload-writer calls per sender.
// Usage: -postScript SummarizeMessageSenderCalls.java CONSTRUCTOR WRITER [WRITER ...]
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class SummarizeMessageSenderCalls extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException("Pass constructor and one or more writer addresses");
        }
        Function constructor = functionAt(args[0]);
        List<Function> writers = new ArrayList<>();
        for (int index = 1; index < args.length; index++) writers.add(functionAt(args[index]));

        Map<Address, Function> owners = new LinkedHashMap<>();
        ReferenceIterator refs = currentProgram.getReferenceManager()
            .getReferencesTo(constructor.getEntryPoint());
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
        int matched = 0;
        try {
            for (Function owner : owners.values()) {
                if (monitor.isCancelled()) break;
                DecompileResults result = decompiler.decompileFunction(owner, 8, monitor);
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) continue;
                completed++;
                String code = result.getDecompiledFunction().getC();
                boolean hasWriter = false;
                for (Function writer : writers) {
                    if (code.contains(writer.getName() + "(")) {
                        hasWriter = true;
                        break;
                    }
                }
                if (!hasWriter) continue;
                matched++;
                String[] lines = code.split("\\R");
                println("OWNER=" + owner.getEntryPoint() + " SIGNATURE=" + lines[0].trim());
                for (String line : lines) {
                    if (line.contains(constructor.getName() + "(")) {
                        println("  CONSTRUCTOR=" + line.trim());
                    }
                    for (Function writer : writers) {
                        if (line.contains(writer.getName() + "(")) {
                            println("  WRITER=" + line.trim());
                        }
                    }
                }
            }
        }
        finally {
            decompiler.dispose();
        }
        println("SUMMARY OWNERS=" + owners.size() + " COMPLETED=" + completed +
            " MATCHED=" + matched);
    }

    private Function functionAt(String hex) throws Exception {
        Address address = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(hex);
        Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
        if (function == null) throw new IllegalArgumentException("No function at " + address);
        return function;
    }
}
