// Read-only excerpts of a native function around a chosen decompiler token.
// Usage: -postScript InspectDecompileWindow.java 1801971A0 DAT_181454640

import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;

public class InspectDecompileWindow extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException("Pass function address and search token");
        }
        Address address = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Function function = currentProgram.getFunctionManager().getFunctionContaining(address);
        if (function == null) {
            println("FUNCTION=<none>");
            return;
        }
        println("FUNCTION=" + function.getName() + " ENTRY=" + function.getEntryPoint());
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
            if (!result.decompileCompleted() || result.getDecompiledFunction() == null) {
                println("DECOMPILE_COMPLETED=false ERROR=" + result.getErrorMessage());
                return;
            }
            String code = result.getDecompiledFunction().getC();
            String[] lines = code.split("\\R");
            println("DECOMPILE_COMPLETED=true LINES=" + lines.length);
            for (int i = 0; i < lines.length; i++) {
                if (lines[i].contains(args[1])) {
                    int start = Math.max(0, i - 12);
                    int end = Math.min(lines.length, i + 18);
                    println("WINDOW=" + (i + 1));
                    for (int j = start; j < end; j++) {
                        println((j + 1) + ": " + lines[j]);
                    }
                }
            }
        } finally {
            decompiler.dispose();
        }
    }
}
