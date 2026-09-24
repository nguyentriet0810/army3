// Read-only scan of functions referencing the endpoint class pointer.
// Usage: -postScript InspectEndpointWrites.java 181454640

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class InspectEndpointWrites extends GhidraScript {
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
        Pattern assignment = Pattern.compile(
            "(?m)^.{0,180}" + Pattern.quote(pointer) +
            ".{0,140}\\+ 0x(20|28)\\)\\s*=.{0,180}$");
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        int completed = 0;
        int matches = 0;
        try {
            for (Function function : functions.values()) {
                if (monitor.isCancelled()) {
                    break;
                }
                DecompileResults result = decompiler.decompileFunction(function, 8, monitor);
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    println("INCOMPLETE=" + function.getEntryPoint());
                    continue;
                }
                completed++;
                String code = result.getDecompiledFunction().getC();
                Matcher matcher = assignment.matcher(code);
                while (matcher.find()) {
                    println("ASSIGNMENT=" + function.getEntryPoint() + " " +
                        matcher.group().trim());
                    matches++;
                }
            }
        } finally {
            decompiler.dispose();
        }
        println("DECOMPILED=" + completed + " MATCHES=" + matches);
    }
}
