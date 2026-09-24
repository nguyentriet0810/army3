// Read-only map of 32-bit RVA jump-table entries.
// Usage: -postScript InspectJumpTable.java 180256C88 254 126
// The example command byte is signed 8-bit and index = signedByte + bias.

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.mem.Memory;
import java.util.HashSet;
import java.util.Set;

public class InspectJumpTable extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 3) {
            throw new IllegalArgumentException("Pass table address, count, bias");
        }
        int count = Integer.parseInt(args[1]);
        int bias = Integer.parseInt(args[2]);
        if (count < 1 || count > 512) {
            throw new IllegalArgumentException("Count must be 1..512");
        }
        Address table = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        Address imageBase = currentProgram.getImageBase();
        Memory memory = currentProgram.getMemory();
        Set<String> uniqueTargets = new HashSet<>();
        Set<String> uniqueDestinations = new HashSet<>();
        int mapped = 0;
        int decoded = 0;
        int directStubs = 0;
        for (int index = 0; index < count && !monitor.isCancelled(); index++) {
            Address entry = table.add(4L * index);
            byte[] raw = new byte[4];
            memory.getBytes(entry, raw);
            long rva = (raw[0] & 0xffL) |
                ((raw[1] & 0xffL) << 8) |
                ((raw[2] & 0xffL) << 16) |
                ((raw[3] & 0xffL) << 24);
            Address target = imageBase.add(rva);
            uniqueTargets.add(target.toString());
            boolean isMapped = memory.contains(target);
            if (isMapped) {
                mapped++;
            }
            Instruction instruction = currentProgram.getListing()
                .getInstructionAt(target);
            if (instruction != null) {
                decoded++;
            }
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(target);
            byte[] stub = new byte[5];
            memory.getBytes(target, stub);
            String destination = "<not-E9>";
            if ((stub[0] & 0xff) == 0xe9) {
                int displacement = (stub[1] & 0xff) |
                    ((stub[2] & 0xff) << 8) |
                    ((stub[3] & 0xff) << 16) |
                    ((stub[4] & 0xff) << 24);
                Address branchTarget = target.add(5L + displacement);
                destination = branchTarget.toString();
                uniqueDestinations.add(destination);
                directStubs++;
            }
            int signedByte = index - bias;
            String command = signedByte >= -128 && signedByte <= 127
                ? String.format("%02X", signedByte & 0xff)
                : "--";
            println("ENTRY=" + index + " BYTE=" + command +
                " TARGET=" + target + " DEST=" + destination +
                " MAPPED=" + isMapped +
                " INSTRUCTION=" + (instruction != null) +
                " FUNCTION=" + (function == null ? "<none>" : function.getName()));
        }
        println("SUMMARY COUNT=" + count + " UNIQUE=" +
            uniqueTargets.size() + " MAPPED=" + mapped +
            " DECODED=" + decoded + " E9_STUBS=" + directStubs +
            " UNIQUE_DEST=" + uniqueDestinations.size() +
            " IMAGE_BASE=" + imageBase);
    }
}
