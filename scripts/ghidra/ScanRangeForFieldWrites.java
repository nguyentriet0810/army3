// Read-only raw scan for likely x86-64 object-field writes in a bounded range.
// It can find instructions in undefined jump-table cases, but scanning every byte
// may produce false instruction boundaries; every hit must be checked in context.
// Usage: -postScript ScanRangeForFieldWrites.java START END 84 88 1d0 1d4 298 29c
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.*;

public class ScanRangeForFieldWrites extends GhidraScript {
    private static final Set<String> WRITE_MNEMONICS = new HashSet<>(Arrays.asList(
        "MOV", "MOVSS", "MOVSD", "MOVUPS", "MOVAPS", "MOVD", "MOVQ",
        "ADD", "ADC", "SUB", "SBB", "INC", "DEC", "AND", "OR", "XOR",
        "XCHG", "CMPXCHG", "IMUL", "SHL", "SHR", "SAR", "SAL", "ROL",
        "ROR", "NOT", "NEG"
    ));

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException("Pass start, exclusive end and displacements");
        }
        Address start = parse(args[0]);
        Address end = parse(args[1]);
        LinkedHashMap<String, String> needles = new LinkedHashMap<>();
        for (int i = 2; i < args.length; i++) {
            String value = args[i].toLowerCase(Locale.ROOT).replaceFirst("^0x", "");
            needles.put(value, "+ 0x" + value + "]");
        }

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        int matches = 0;
        for (Address at = start; at.compareTo(end) < 0 && !monitor.isCancelled(); at = at.add(1)) {
            PseudoInstruction instruction;
            try {
                instruction = decoder.disassemble(at);
            } catch (Exception ignored) {
                continue;
            }
            if (instruction == null || instruction.getLength() < 1) continue;
            String mnemonic = instruction.getMnemonicString().toUpperCase(Locale.ROOT);
            if (!WRITE_MNEMONICS.contains(mnemonic)) continue;
            String text = instruction.toString();
            String lower = text.toLowerCase(Locale.ROOT);
            int comma = lower.indexOf(',');
            String destination = comma < 0 ? lower : lower.substring(0, comma);
            if (!destination.contains("[") || destination.contains("[rsp") ||
                destination.contains("[rbp") || destination.contains("[esp") ||
                destination.contains("[ebp")) continue;
            for (Map.Entry<String, String> entry : needles.entrySet()) {
                if (!destination.contains(entry.getValue())) continue;
                println("CANDIDATE_WRITE=0x" + entry.getKey() + " AT=" + at +
                    " LENGTH=" + instruction.getLength() + " TEXT=" + text);
                matches++;
                break;
            }
        }
        println("START=" + start + " END=" + end + " MATCHES=" + matches);
    }

    private Address parse(String value) throws Exception {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
    }
}
