// Find instructions containing selected text while traversing a bounded CFG.
// Usage: -postScript FindPseudoInstructions.java START END TOKEN [TOKEN ...]
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.*;

public class FindPseudoInstructions extends GhidraScript {
    private static final int LIMIT = 12000;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException("Pass START END and one or more TOKEN values");
        }
        Address start = parse(args[0]);
        Address end = parse(args[1]);
        if (start.compareTo(end) >= 0) {
            throw new IllegalArgumentException("Require START < END");
        }

        List<String> tokens = new ArrayList<>();
        for (int i = 2; i < args.length; i++) {
            tokens.add(args[i].toUpperCase(Locale.ROOT));
        }

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        ArrayDeque<Address> queue = new ArrayDeque<>();
        TreeSet<Address> seen = new TreeSet<>();
        int errors = 0;
        int matches = 0;
        queue.add(start);

        while (!queue.isEmpty() && seen.size() < LIMIT && !monitor.isCancelled()) {
            Address at = queue.removeFirst();
            if (!inside(at, start, end) || !seen.add(at)) continue;

            PseudoInstruction instruction;
            try {
                instruction = decoder.disassemble(at);
            } catch (Exception exception) {
                errors++;
                continue;
            }
            if (instruction == null || instruction.getLength() < 1) {
                errors++;
                continue;
            }

            String text = instruction.toString();
            String upper = text.toUpperCase(Locale.ROOT);
            for (String token : tokens) {
                if (upper.contains(token)) {
                    println("MATCH=" + at + " TOKEN=" + token + " " + text);
                    matches++;
                    break;
                }
            }

            if (instruction.getFlowType().isJump()) {
                for (Address target : instruction.getFlows()) {
                    if (inside(target, start, end)) queue.addLast(target);
                }
            }
            Address fallthrough = instruction.getFallThrough();
            if (inside(fallthrough, start, end)) queue.addLast(fallthrough);
        }

        println("START=" + start + " END=" + end + " VISITED=" + seen.size() +
            " MATCHES=" + matches + " ERRORS=" + errors + " LIMIT=" + LIMIT);
    }

    private Address parse(String value) throws Exception {
        String normalized = value.toLowerCase(Locale.ROOT).replaceFirst("^0x", "");
        return currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(normalized);
    }

    private boolean inside(Address address, Address start, Address end) {
        return address != null && address.compareTo(start) >= 0 && address.compareTo(end) < 0;
    }
}
