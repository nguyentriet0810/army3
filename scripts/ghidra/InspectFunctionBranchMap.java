// Read-only, bounded instruction map for a function too large to decompile.
// Usage: -postScript InspectFunctionBranchMap.java 1801FCED4

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;

public class InspectFunctionBranchMap extends GhidraScript {
    private static final int MAX_COMPARE_LINES = 300;
    private static final int MAX_CALL_LINES = 180;
    private static final int MAX_BRANCH_LINES = 200;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException("Pass one hexadecimal address");
        }
        Address address = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Function function = currentProgram.getFunctionManager()
            .getFunctionContaining(address);
        if (function == null) {
            println("FUNCTION=<none>");
            return;
        }
        println("FUNCTION=" + function.getName() + " ENTRY=" +
            function.getEntryPoint() + " BODY=" +
            function.getBody().getNumAddresses());

        int compareCount = 0;
        int callCount = 0;
        int branchCount = 0;
        int otherCount = 0;
        Address lastAddress = null;
        InstructionIterator iterator = currentProgram.getListing()
            .getInstructions(function.getBody(), true);
        while (iterator.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = iterator.next();
            lastAddress = instruction.getAddress();
            String mnemonic = instruction.getMnemonicString().toUpperCase();
            if (mnemonic.equals("CMP") || mnemonic.equals("TEST")) {
                if (compareCount < MAX_COMPARE_LINES) {
                    println("COMPARE=" + instruction.getAddress() + " " +
                        instruction.toString());
                }
                compareCount++;
            } else if (instruction.getFlowType().isCall()) {
                for (Reference reference : instruction.getReferencesFrom()) {
                    if (!reference.getReferenceType().isCall()) {
                        continue;
                    }
                    if (callCount < MAX_CALL_LINES) {
                        println("CALL=" + instruction.getAddress() +
                            " TARGET=" + reference.getToAddress());
                    }
                    callCount++;
                }
            } else if (mnemonic.startsWith("J")) {
                if (branchCount < MAX_BRANCH_LINES) {
                    println("BRANCH=" + instruction.getAddress() + " " +
                        instruction.toString());
                }
                branchCount++;
            } else {
                otherCount++;
            }
        }
        println("COUNTS COMPARES=" + compareCount + " CALLS=" + callCount +
            " BRANCHES=" + branchCount + " OTHER=" + otherCount +
            " LAST=" + lastAddress + " LIMITS=" + MAX_COMPARE_LINES +
            "," + MAX_CALL_LINES + "," + MAX_BRANCH_LINES);
    }
}
