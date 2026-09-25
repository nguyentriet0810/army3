// Read-only bounded CFG summary for code that Ghidra did not define as functions.
// Usage: -postScript SummarizePseudoCfg.java 180255E52 180256C55
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.*;

public class SummarizePseudoCfg extends GhidraScript {
    private static final int LIMIT = 12000;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 2) {
            throw new IllegalArgumentException("Pass start and exclusive end");
        }
        Address start = parse(args[0]);
        Address end = parse(args[1]);
        if (start.compareTo(end) >= 0) {
            throw new IllegalArgumentException("Require start < end");
        }

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        ArrayDeque<Address> queue = new ArrayDeque<>();
        TreeSet<Address> seen = new TreeSet<>();
        TreeMap<Address, List<Address>> calls = new TreeMap<>();
        TreeMap<Address, String> writes = new TreeMap<>();
        TreeMap<Address, String> compares = new TreeMap<>();
        TreeMap<Address, String> exits = new TreeMap<>();
        int errors = 0;
        int indirect = 0;
        queue.add(start);

        while (!queue.isEmpty() && seen.size() < LIMIT && !monitor.isCancelled()) {
            Address at = queue.removeFirst();
            if (!inside(at, start, end) || !seen.add(at)) continue;
            PseudoInstruction insn;
            try {
                insn = decoder.disassemble(at);
            } catch (Exception exception) {
                errors++;
                continue;
            }
            if (insn == null || insn.getLength() < 1) {
                errors++;
                continue;
            }

            String text = insn.toString();
            String upper = text.toUpperCase(Locale.ROOT);
            if ((upper.startsWith("MOV ") || upper.startsWith("MOVZX ") ||
                    upper.startsWith("MOVSX ") || upper.startsWith("LEA ") ||
                    upper.startsWith("XOR ") || upper.startsWith("OR ") ||
                    upper.startsWith("AND ") || upper.startsWith("ADD ") ||
                    upper.startsWith("SUB ") || upper.startsWith("INC ") ||
                    upper.startsWith("DEC ") || upper.startsWith("BTS ") ||
                    upper.startsWith("CMPXCHG ")) && firstOperandIsMemory(text)) {
                writes.put(at, text);
            }
            if (upper.startsWith("CMP ") || upper.startsWith("TEST ")) {
                compares.put(at, text);
            }

            if (insn.getFlowType().isCall()) {
                Address[] flows = insn.getFlows();
                if (flows.length == 0 || insn.getFlowType().isComputed()) {
                    indirect++;
                } else {
                    for (Address target : flows) {
                        calls.computeIfAbsent(target, ignored -> new ArrayList<>()).add(at);
                    }
                }
            }
            if (insn.getFlowType().isJump()) {
                Address[] flows = insn.getFlows();
                if (flows.length == 0 || insn.getFlowType().isComputed()) {
                    indirect++;
                } else {
                    for (Address target : flows) {
                        if (inside(target, start, end)) queue.addLast(target);
                        else exits.put(at, text + " -> " + target);
                    }
                }
            }
            Address fall = insn.getFallThrough();
            if (inside(fall, start, end)) queue.addLast(fall);
            else if (fall != null && !insn.getFlowType().isCall()) {
                exits.put(at, text + " FALLTHROUGH->" + fall);
            }
        }

        println("START=" + start + " END=" + end + " VISITED=" + seen.size() +
            " ERRORS=" + errors + " INDIRECT=" + indirect + " LIMIT=" + LIMIT);
        for (Map.Entry<Address, List<Address>> entry : calls.entrySet()) {
            println("CALL_TARGET=" + entry.getKey() + " COUNT=" + entry.getValue().size() +
                " SITES=" + join(entry.getValue()));
        }
        for (Map.Entry<Address, String> entry : writes.entrySet()) {
            println("WRITE=" + entry.getKey() + " " + entry.getValue());
        }
        for (Map.Entry<Address, String> entry : compares.entrySet()) {
            println("COMPARE=" + entry.getKey() + " " + entry.getValue());
        }
        for (Map.Entry<Address, String> entry : exits.entrySet()) {
            println("EXIT=" + entry.getKey() + " " + entry.getValue());
        }
    }

    private Address parse(String value) throws Exception {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
    }

    private boolean inside(Address at, Address start, Address end) {
        return at != null && at.compareTo(start) >= 0 && at.compareTo(end) < 0;
    }

    private boolean firstOperandIsMemory(String text) {
        int space = text.indexOf(' ');
        int comma = text.indexOf(',');
        if (space < 0 || comma < 0 || comma <= space) return false;
        String first = text.substring(space + 1, comma);
        return first.indexOf('[') >= 0 && first.indexOf(']') >= 0;
    }

    private String join(List<Address> addresses) {
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < addresses.size(); i++) {
            if (i != 0) out.append(',');
            out.append(addresses.get(i));
        }
        return out.toString();
    }
}
