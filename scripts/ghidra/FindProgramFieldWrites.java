// Read-only inventory of likely native writes to selected object displacements.
// Usage: -postScript FindProgramFieldWrites.java 84 88 1d0 1d4 298 29c
//
// This is a syntactic x86-64 filter, not type recovery. It excludes stack-based
// operands and reports the containing function so results can be checked against
// the expected object layout in the decompiler.
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.util.*;

public class FindProgramFieldWrites extends GhidraScript {
    private static final Set<String> WRITE_MNEMONICS = new HashSet<>(Arrays.asList(
        "mov", "movss", "movsd", "movups", "movaps", "movd", "movq",
        "add", "adc", "sub", "sbb", "inc", "dec", "and", "or", "xor",
        "xchg", "cmpxchg", "imul", "shl", "shr", "sar", "sal", "rol",
        "ror", "not", "neg"
    ));

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Pass one or more hex displacements");
        }

        LinkedHashMap<String, String> needles = new LinkedHashMap<>();
        for (String argument : args) {
            String value = argument.toLowerCase(Locale.ROOT).replaceFirst("^0x", "");
            needles.put(value, "+ 0x" + value + "]");
        }

        TreeMap<String, TreeSet<String>> offsetsByFunction = new TreeMap<>();
        TreeMap<String, Integer> countsByFunction = new TreeMap<>();
        int total = 0;

        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            String mnemonic = instruction.getMnemonicString().toLowerCase(Locale.ROOT);
            if (!WRITE_MNEMONICS.contains(mnemonic)) continue;

            String text = instruction.toString();
            String lower = text.toLowerCase(Locale.ROOT);
            int comma = lower.indexOf(',');
            String destination = comma < 0 ? lower : lower.substring(0, comma);
            if (!destination.contains("[")) continue;
            if (destination.contains("[rsp") || destination.contains("[rbp") ||
                destination.contains("[esp") || destination.contains("[ebp")) continue;

            String matched = null;
            for (Map.Entry<String, String> entry : needles.entrySet()) {
                if (destination.contains(entry.getValue())) {
                    matched = entry.getKey();
                    break;
                }
            }
            if (matched == null) continue;

            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            String functionName = function == null
                ? "<none>"
                : function.getName() + "@" + function.getEntryPoint();
            println("WRITE=0x" + matched + " AT=" + instruction.getAddress() +
                " FUNCTION=" + functionName + " TEXT=" + text);
            offsetsByFunction.computeIfAbsent(functionName, key -> new TreeSet<>()).add(matched);
            countsByFunction.put(functionName, countsByFunction.getOrDefault(functionName, 0) + 1);
            total++;
        }

        println("SUMMARY_TOTAL=" + total);
        for (Map.Entry<String, TreeSet<String>> entry : offsetsByFunction.entrySet()) {
            println("SUMMARY_FUNCTION=" + entry.getKey() + " OFFSETS=" +
                String.join(",", entry.getValue()) + " WRITES=" +
                countsByFunction.get(entry.getKey()));
        }
    }
}
