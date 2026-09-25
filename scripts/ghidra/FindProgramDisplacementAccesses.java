// Read-only inventory of instructions using selected hexadecimal displacements.
// Usage: -postScript FindProgramDisplacementAccesses.java 1d8 168
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import java.util.*;

public class FindProgramDisplacementAccesses extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Pass one or more hex displacements");
        }

        LinkedHashMap<String, List<String>> needles = new LinkedHashMap<>();
        for (String argument : args) {
            String value = argument.toLowerCase(Locale.ROOT).replaceFirst("^0x", "");
            needles.put(value, Arrays.asList("+ 0x" + value + "]", "- 0x" + value + "]"));
        }

        TreeMap<String, Integer> counts = new TreeMap<>();
        int total = 0;
        InstructionIterator instructions = currentProgram.getListing().getInstructions(true);
        while (instructions.hasNext() && !monitor.isCancelled()) {
            Instruction instruction = instructions.next();
            String text = instruction.toString();
            String lower = text.toLowerCase(Locale.ROOT);
            String matched = null;
            for (Map.Entry<String, List<String>> entry : needles.entrySet()) {
                for (String needle : entry.getValue()) {
                    if (lower.contains(needle)) {
                        matched = entry.getKey();
                        break;
                    }
                }
                if (matched != null) break;
            }
            if (matched == null) continue;

            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(instruction.getAddress());
            String functionName = function == null
                ? "<none>"
                : function.getName() + "@" + function.getEntryPoint();
            println("DISP=0x" + matched + " AT=" + instruction.getAddress() +
                " FUNCTION=" + functionName + " TEXT=" + text);
            String key = matched + " " + functionName;
            counts.put(key, counts.getOrDefault(key, 0) + 1);
            total++;
        }

        println("SUMMARY_TOTAL=" + total);
        for (Map.Entry<String, Integer> entry : counts.entrySet()) {
            println("SUMMARY=" + entry.getKey() + " COUNT=" + entry.getValue());
        }
    }
}
