// Read-only headless script to list references to a native data address.
// Usage: -postScript InspectDataReferences.java 181454640

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectDataReferences extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length != 1) {
            throw new IllegalArgumentException("Pass one hexadecimal data address");
        }
        Address address = currentProgram.getAddressFactory()
            .getDefaultAddressSpace().getAddress(args[0]);
        ReferenceIterator references = currentProgram.getReferenceManager()
            .getReferencesTo(address);
        int count = 0;
        while (references.hasNext() && !monitor.isCancelled()) {
            Reference reference = references.next();
            Function owner = currentProgram.getFunctionManager()
                .getFunctionContaining(reference.getFromAddress());
            println("REF=" + reference.getFromAddress() + " TYPE=" +
                reference.getReferenceType() + " FUNCTION=" +
                (owner == null ? "<none>" : owner.getEntryPoint()));
            count++;
            if (count >= 500) {
                println("TRUNCATED=true");
                break;
            }
        }
        println("REFERENCE_COUNT_SHOWN=" + count);
    }
}
