// Read-only inventory of references to one or more native function entries.
// Usage: -postScript InspectIncomingReferences.java 180449900 180519910
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;

public class InspectIncomingReferences extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Pass one or more hexadecimal function addresses");
        }

        for (String hex : args) {
            Address query = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(hex);
            Function target = currentProgram.getFunctionManager().getFunctionContaining(query);
            println("QUERY=" + query + " TARGET=" +
                (target == null ? "<none>" : target.getName() + "@" + target.getEntryPoint()));
            if (target == null) continue;

            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(target.getEntryPoint());
            int count = 0;
            while (references.hasNext() && !monitor.isCancelled()) {
                Reference reference = references.next();
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                println("REF=" + reference.getFromAddress() + " TYPE=" +
                    reference.getReferenceType() + " OWNER=" +
                    (owner == null ? "<none>" : owner.getName() + "@" + owner.getEntryPoint()));
                count++;
            }
            println("REFERENCE_COUNT=" + count);
        }
    }
}
