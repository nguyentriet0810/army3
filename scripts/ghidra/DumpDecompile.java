// Read-only full decompile dump for one or more native addresses.
// Usage: -postScript DumpDecompile.java 180459240 [more hex addresses]

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class DumpDecompile extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Pass one or more hexadecimal addresses");
        }

        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (String hex : args) {
                Address address = currentProgram.getAddressFactory()
                    .getDefaultAddressSpace().getAddress(hex);
                Function function = currentProgram.getFunctionManager()
                    .getFunctionContaining(address);
                println("QUERY=" + address + " FUNCTION=" +
                    (function == null ? "<none>" : function.getName()));
                if (function == null) {
                    continue;
                }

                DecompileResults result = decompiler.decompileFunction(function, 90, monitor);
                if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                    println("DECOMPILE_COMPLETED=false ERROR=" + result.getErrorMessage());
                    continue;
                }

                String code = result.getDecompiledFunction().getC();
                println("DECOMPILE_COMPLETED=true LENGTH=" + code.length());
                println("BEGIN_DECOMPILE=" + function.getEntryPoint());
                println(code);
                println("END_DECOMPILE=" + function.getEntryPoint());
            }
        }
        finally {
            decompiler.dispose();
        }
    }
}
