// Read-only ordered inventory of selected direct calls in a bounded pseudo-CFG.
// Usage: -postScript SummarizeReaderSequence.java START END ADDRESS:LABEL [...]
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.*;

public class SummarizeReaderSequence extends GhidraScript {
    private static final int LIMIT = 20000;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "Pass START END and one or more ADDRESS:LABEL targets");
        }

        Address start = parse(args[0]);
        Address end = parse(args[1]);
        TreeMap<Address, String> targets = new TreeMap<>();
        for (int index = 2; index < args.length; index++) {
            String[] pair = args[index].split(":", 2);
            if (pair.length != 2 || pair[1].isEmpty()) {
                throw new IllegalArgumentException(
                    "Target must use ADDRESS:LABEL: " + args[index]);
            }
            targets.put(parse(pair[0]), pair[1]);
        }

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        ArrayDeque<Address> queue = new ArrayDeque<>();
        TreeSet<Address> seen = new TreeSet<>();
        TreeMap<Address, String> matches = new TreeMap<>();
        queue.add(start);

        while (!queue.isEmpty() && seen.size() < LIMIT && !monitor.isCancelled()) {
            Address at = queue.removeFirst();
            if (at.compareTo(start) < 0 || at.compareTo(end) >= 0 || !seen.add(at)) {
                continue;
            }

            PseudoInstruction instruction = decoder.disassemble(at);
            if (instruction == null || instruction.getLength() < 1) continue;

            Address fallThrough = instruction.getFallThrough();
            if (fallThrough != null) queue.addLast(fallThrough);

            for (Address flow : instruction.getFlows()) {
                if (instruction.getFlowType().isCall()) {
                    String label = targets.get(flow);
                    if (label != null) matches.put(at, label + " TARGET=" + flow);
                } else {
                    queue.addLast(flow);
                }
            }
        }

        println("START=" + start + " END=" + end + " VISITED=" + seen.size() +
            " MATCHES=" + matches.size() + " LIMIT=" + LIMIT);
        int ordinal = 0;
        for (Map.Entry<Address, String> match : matches.entrySet()) {
            println("READ=" + ordinal + " SITE=" + match.getKey() + " " +
                match.getValue());
            ordinal++;
        }
    }

    private Address parse(String value) throws Exception {
        String normalized = value.toLowerCase(Locale.ROOT).replaceFirst("^0x", "");
        return currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(normalized);
    }
}
