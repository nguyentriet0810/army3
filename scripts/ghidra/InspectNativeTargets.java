// Read-only Ghidra headless script for selected addresses from Cpp2IL ISIL.
// Usage: -postScript InspectNativeTargets.java 1804DF68F [more hex addresses]

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectNativeTargets extends GhidraScript {
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
                println("ENTRY=" + function.getEntryPoint() + " BODY=" +
                    function.getBody().getNumAddresses());

                ReferenceIterator callers = currentProgram.getReferenceManager()
                    .getReferencesTo(function.getEntryPoint());
                int callerCount = 0;
                while (callers.hasNext() && callerCount < 20) {
                    Reference reference = callers.next();
                    println("CALLER=" + reference.getFromAddress() + " TYPE=" +
                        reference.getReferenceType());
                    callerCount++;
                }

                InstructionIterator instructions = currentProgram.getListing()
                    .getInstructions(function.getBody(), true);
                int calls = 0;
                while (instructions.hasNext() && !monitor.isCancelled() && calls < 100) {
                    Instruction instruction = instructions.next();
                    if (!instruction.getFlowType().isCall()) {
                        continue;
                    }
                    for (Reference reference : instruction.getReferencesFrom()) {
                        if (reference.getReferenceType().isCall()) {
                            println("CALL=" + instruction.getAddress() + " TARGET=" +
                                reference.getToAddress());
                            calls++;
                        }
                    }
                }

                DecompileResults result = decompiler.decompileFunction(function, 45, monitor);
                if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    String code = result.getDecompiledFunction().getC();
                    println("DECOMPILE_COMPLETED=true LENGTH=" + code.length());
                    println(code.substring(0, Math.min(12000, code.length())));
                } else {
                    println("DECOMPILE_COMPLETED=false ERROR=" + result.getErrorMessage());
                }
            }
        } finally {
            decompiler.dispose();
        }
    }
}
