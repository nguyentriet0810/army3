// Read-only raw scan for x86-64 computed calls containing selected operand text.
// Usage: -postScript ScanRangeForComputedCalls.java START END TOKEN [TOKEN ...]
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

public class ScanRangeForComputedCalls extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException("Pass start, exclusive end and operand token(s)");
        }
        Address start = parse(args[0]);
        Address end = parse(args[1]);
        List<String> tokens = new ArrayList<>();
        for (int index = 2; index < args.length; index++) {
            tokens.add(args[index].toUpperCase(Locale.ROOT));
        }

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        int candidates = 0;
        int matches = 0;
        for (Address at = start; at.compareTo(end) < 0 && !monitor.isCancelled(); at = at.add(1)) {
            try {
                if ((getByte(at) & 0xff) != 0xff) continue;
            }
            catch (Exception ignored) {
                // A broad image range can contain gaps between mapped blocks.
                continue;
            }
            PseudoInstruction instruction;
            try {
                instruction = decoder.disassemble(at);
            }
            catch (Exception ignored) {
                continue;
            }
            if (instruction == null || !instruction.getFlowType().isCall() ||
                !instruction.getFlowType().isComputed()) continue;
            candidates++;
            String text = instruction.toString();
            String upper = text.toUpperCase(Locale.ROOT);
            for (String token : tokens) {
                if (!upper.contains(token)) continue;
                println("CALL=" + at + " TOKEN=" + token + " TEXT=" + text);
                matches++;
                break;
            }
        }
        println("START=" + start + " END=" + end + " COMPUTED_CALLS=" +
            candidates + " MATCHES=" + matches);
    }

    private Address parse(String value) throws Exception {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
    }
}
