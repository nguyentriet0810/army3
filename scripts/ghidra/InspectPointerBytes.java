// Read-only byte inspection for native data pointers; never executes client code.
// Usage: -postScript InspectPointerBytes.java 1814544E0 1814544D8

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.mem.Memory;

public class InspectPointerBytes extends GhidraScript {
    @Override
    public void run() throws Exception {
        Memory memory = currentProgram.getMemory();
        for (String hex : getScriptArgs()) {
            Address address = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(hex);
            byte[] raw = new byte[8];
            memory.getBytes(address, raw);
            long value = 0;
            for (int i = 0; i < 8; i++) {
                value |= (long)(raw[i] & 0xff) << (8 * i);
            }
            println("POINTER_AT=" + address + " VALUE=0x" +
                Long.toHexString(value));
            if (value == 0) {
                continue;
            }
            Address target = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(Long.toHexString(value));
            if (!memory.contains(target)) {
                println("TARGET_UNMAPPED=" + target);
                continue;
            }
            byte[] data = new byte[24];
            int count = memory.getBytes(target, data);
            StringBuilder builder = new StringBuilder();
            for (int i = 0; i < count; i++) {
                builder.append(String.format("%02X", data[i] & 0xff));
            }
            println("TARGET=" + target + " FIRST_BYTES=" + builder);
        }
    }
}
