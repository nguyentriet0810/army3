// Read-only linear pseudo-disassembly after selected call sites.
// Usage: -postScript InspectPseudoCallWindows.java COUNT SITE [SITE ...]
import ghidra.app.script.GhidraScript;
import ghidra.app.util.PseudoDisassembler;
import ghidra.app.util.PseudoInstruction;
import ghidra.program.model.address.Address;
import java.util.Locale;

public class InspectPseudoCallWindows extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 2) {
            throw new IllegalArgumentException("Pass COUNT and one or more SITE addresses");
        }
        int count = Integer.parseInt(args[0]);
        if (count < 1 || count > 80) {
            throw new IllegalArgumentException("COUNT must be 1..80");
        }

        PseudoDisassembler decoder = new PseudoDisassembler(currentProgram);
        for (int index = 1; index < args.length; index++) {
            Address cursor = parse(args[index]);
            println("WINDOW=" + cursor + " COUNT=" + count);
            for (int step = 0; step < count && !monitor.isCancelled(); step++) {
                PseudoInstruction instruction = decoder.disassemble(cursor);
                if (instruction == null || instruction.getLength() < 1) {
                    println("STOP=" + cursor + " ERROR=no instruction");
                    break;
                }
                println("AT=" + cursor + " " + instruction.toString());
                cursor = cursor.add(instruction.getLength());
            }
        }
    }

    private Address parse(String value) throws Exception {
        String normalized = value.toLowerCase(Locale.ROOT).replaceFirst("^0x", "");
        return currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(normalized);
    }
}
