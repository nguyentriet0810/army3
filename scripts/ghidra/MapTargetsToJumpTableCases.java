// Read-only CFG mapping from jump-table command entries to selected addresses.
// Usage: -postScript MapTargetsToJumpTableCases.java TABLE COUNT BIAS RANGE_START RANGE_END TARGET...
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;
import java.util.*;

public class MapTargetsToJumpTableCases extends GhidraScript {
    private static final int LIMIT_PER_CASE = 30000;

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 6) {
            throw new IllegalArgumentException(
                "Pass table, count, bias, range start/end and one or more targets");
        }
        Address table = parse(args[0]);
        int count = Integer.parseInt(args[1]);
        int bias = Integer.parseInt(args[2]);
        Address rangeStart = parse(args[3]);
        Address rangeEnd = parse(args[4]);
        LinkedHashSet<Address> targets = new LinkedHashSet<>();
        for (int i = 5; i < args.length; i++) targets.add(parse(args[i]));

        Memory memory = currentProgram.getMemory();
        Address imageBase = currentProgram.getImageBase();
        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        TreeMap<Address, ArrayList<String>> bytesByDestination = new TreeMap<>();

        for (int index = 0; index < count; index++) {
            byte[] raw = new byte[4];
            memory.getBytes(table.add(4L * index), raw);
            long rva = (raw[0] & 0xffL) | ((raw[1] & 0xffL) << 8) |
                ((raw[2] & 0xffL) << 16) | ((raw[3] & 0xffL) << 24);
            Address stub = imageBase.add(rva);
            byte[] jump = new byte[5];
            memory.getBytes(stub, jump);
            if ((jump[0] & 0xff) != 0xe9) continue;
            int displacement = (jump[1] & 0xff) | ((jump[2] & 0xff) << 8) |
                ((jump[3] & 0xff) << 16) | ((jump[4] & 0xff) << 24);
            Address destination = stub.add(5L + displacement);
            int signedByte = index - bias;
            String command = signedByte >= -128 && signedByte <= 127
                ? String.format("%02X", signedByte & 0xff) : "--";
            bytesByDestination.computeIfAbsent(destination, ignored -> new ArrayList<>())
                .add(command);
        }

        for (Map.Entry<Address, ArrayList<String>> caseEntry : bytesByDestination.entrySet()) {
            Address start = caseEntry.getKey();
            if (!inside(start, rangeStart, rangeEnd)) continue;
            ArrayDeque<Address> queue = new ArrayDeque<>();
            HashSet<Address> seen = new HashSet<>();
            LinkedHashSet<Address> reached = new LinkedHashSet<>();
            TreeSet<Address> indirectSites = new TreeSet<>();
            int errors = 0;
            int indirect = 0;
            queue.add(start);

            while (!queue.isEmpty() && seen.size() < LIMIT_PER_CASE &&
                    reached.size() < targets.size() && !monitor.isCancelled()) {
                Address at = queue.removeFirst();
                if (!inside(at, rangeStart, rangeEnd) || !seen.add(at)) continue;
                if (targets.contains(at)) reached.add(at);
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
                        indirectSites.add(at);
                    } else {
                        for (Address flow : flows) {
                            if (inside(flow, rangeStart, rangeEnd)) queue.addLast(flow);
                        }
                    }
                }
                Address fall = instruction.getFallThrough();
                if (inside(fall, rangeStart, rangeEnd)) queue.addLast(fall);
            }

            if (!reached.isEmpty()) {
                println("CASE_BYTES=" + String.join(",", caseEntry.getValue()) +
                    " ENTRY=" + start + " REACHED=" + join(reached) +
                    " VISITED=" + seen.size() + " ERRORS=" + errors +
                    " INDIRECT=" + indirect + " INDIRECT_SITES=" + join(indirectSites));
            } else if (!indirectSites.isEmpty()) {
                println("UNRESOLVED_CASE_BYTES=" + String.join(",", caseEntry.getValue()) +
                    " ENTRY=" + start + " VISITED=" + seen.size() +
                    " ERRORS=" + errors + " INDIRECT=" + indirect +
                    " INDIRECT_SITES=" + join(indirectSites));
            }
        }
    }

    private Address parse(String value) throws Exception {
        return currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(value);
    }

    private boolean inside(Address at, Address start, Address end) {
        return at != null && at.compareTo(start) >= 0 && at.compareTo(end) < 0;
    }

    private String join(Collection<Address> addresses) {
        StringBuilder out = new StringBuilder();
        for (Address address : addresses) {
            if (out.length() != 0) out.append(',');
            out.append(address);
        }
        return out.toString();
    }
}
