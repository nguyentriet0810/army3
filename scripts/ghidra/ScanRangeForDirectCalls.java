// Read-only raw scan for x86-64 direct calls to selected targets in a bounded range.
// Useful when Ghidra has not defined every jump-table case as listing code.
// Usage: -postScript ScanRangeForDirectCalls.java START END TARGET [TARGET...]
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.*;

public class ScanRangeForDirectCalls extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException("Pass start, exclusive end and one or more targets");
        }
        Address start = parse(args[0]);
        Address end = parse(args[1]);
        HashSet<Address> targets = new HashSet<>();
        for (int i = 2; i < args.length; i++) targets.add(parse(args[i]));

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        int byteCandidates = 0;
        int matches = 0;
        for (Address at = start; at.compareTo(end) < 0 && !monitor.isCancelled(); at = at.add(1)) {
            if ((getByte(at) & 0xff) != 0xe8) continue;
            byteCandidates++;
            PseudoInstruction instruction;
            try {
                instruction = decoder.disassemble(at);
            } catch (Exception ignored) {
                continue;
            }
            if (instruction == null || !instruction.getFlowType().isCall() ||
                instruction.getFlowType().isComputed()) continue;
            for (Address target : instruction.getFlows()) {
                if (!targets.contains(target)) continue;
                println("CALL=" + at + " TARGET=" + target + " TEXT=" + instruction);
                matches++;
            }
        }
        println("START=" + start + " END=" + end + " BYTE_CANDIDATES=" +
            byteCandidates + " MATCHES=" + matches);
    }

    private Address parse(String value) throws Exception {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
    }
}
