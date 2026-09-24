// Read-only bounded CFG walk: case entry, target instruction, exclusive end.
// Usage: -postScript TracePseudoReachability.java 18022ADB0 18022D28F 18022D329
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.*;

public class TracePseudoReachability extends GhidraScript {
    private static final int LIMIT = 10000;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) {
            throw new IllegalArgumentException("Pass start, target, exclusive end");
        }
        Address start = parseHexAddress(args[0]);
        Address target = parseHexAddress(args[1]);
        Address end = parseHexAddress(args[2]);
        if (start.compareTo(target) > 0 || target.compareTo(end) >= 0) {
            throw new IllegalArgumentException("Require start <= target < end");
        }
        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        ArrayDeque<Address> queue = new ArrayDeque<>();
        HashSet<Address> seen = new HashSet<>();
        HashMap<Address, Address> previous = new HashMap<>();
        previous.put(start, null);
        queue.add(start);
        int errors = 0, indirect = 0;
        boolean reached = false;
        while (!queue.isEmpty() && seen.size() < LIMIT && !monitor.isCancelled()) {
            Address at = queue.removeFirst();
            if (at.compareTo(start) < 0 || at.compareTo(end) >= 0 || !seen.add(at)) {
                continue;
            }
            if (at.equals(target)) {
                reached = true;
                break;
            }
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
            if (instruction.getFlowType().isJump()) {
                Address[] flows = instruction.getFlows();
                if (instruction.getFlowType().isComputed() || flows.length == 0) {
                    indirect++;
                } else {
                    for (Address destination : flows) {
                        enqueue(destination, at, start, end, queue, previous);
                    }
                }
            }
            enqueue(instruction.getFallThrough(), at, start, end, queue, previous);
        }
        println("START=" + start + " TARGET=" + target + " REACHED=" + reached +
            " VISITED=" + seen.size() + " ERRORS=" + errors +
            " INDIRECT=" + indirect + " LIMIT=" + LIMIT);
        if (!reached) return;
        ArrayList<Address> path = new ArrayList<>();
        for (Address at = target; at != null && path.size() <= LIMIT; at = previous.get(at)) {
            path.add(at);
        }
        Collections.reverse(path);
        println("PATH_LENGTH=" + path.size());
        for (int i = 0; i < path.size(); i++) {
            PseudoInstruction instruction = decoder.disassemble(path.get(i));
            if (path.size() <= 2000) {
                println("STEP=" + i + " ADDRESS=" + path.get(i) + " " + instruction);
            }
            if (i == 0 || i == path.size() - 1 ||
                    instruction.getFlowType().isJump() ||
                    instruction.getFlowType().isCall()) {
                println("PATH=" + path.get(i) + " " + instruction);
            }
        }
    }

    private Address parseHexAddress(String hex) throws Exception {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(hex);
    }

    private void enqueue(Address at, Address from, Address start, Address end,
            ArrayDeque<Address> queue, HashMap<Address, Address> previous) {
        if (at == null || at.compareTo(start) < 0 || at.compareTo(end) >= 0 ||
                previous.containsKey(at)) return;
        previous.put(at, from);
        queue.addLast(at);
    }
}
