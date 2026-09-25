// Read-only call-site inventory for one or more native addresses.
// Usage: -postScript InspectCallSites.java 1802870F0 [more addresses]
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.symbol.Reference;

public class InspectCallSites extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length == 0) {
            throw new IllegalArgumentException("Pass one or more hexadecimal addresses");
        }

        for (String hex : args) {
            Address query = currentProgram.getAddressFactory()
                .getDefaultAddressSpace().getAddress(hex);
            Function function = currentProgram.getFunctionManager()
                .getFunctionContaining(query);
            println("QUERY=" + query + " FUNCTION=" +
                (function == null ? "<none>" : function.getName()));
            if (function == null) continue;

            println("ENTRY=" + function.getEntryPoint() + " BODY=" +
                function.getBody().getNumAddresses());
            InstructionIterator instructions = currentProgram.getListing()
                .getInstructions(function.getBody(), true);
            int calls = 0;
            int indirect = 0;
            while (instructions.hasNext() && !monitor.isCancelled()) {
                Instruction instruction = instructions.next();
                if (!instruction.getFlowType().isCall()) continue;

                calls++;
                Address[] flows = instruction.getFlows();
                boolean computed = instruction.getFlowType().isComputed() || flows.length == 0;
                if (computed) indirect++;

                StringBuilder line = new StringBuilder();
                line.append("SITE=").append(instruction.getAddress());
                line.append(" COMPUTED=").append(computed);
                line.append(" TEXT=").append(instruction.toString());
                if (flows.length > 0) {
                    line.append(" FLOWS=");
                    for (int index = 0; index < flows.length; index++) {
                        if (index > 0) line.append(',');
                        line.append(flows[index]);
                    }
                }
                println(line.toString());

                for (Reference reference : instruction.getReferencesFrom()) {
                    if (reference.getReferenceType().isCall()) {
                        println("REFERENCE=" + instruction.getAddress() + " TARGET=" +
                            reference.getToAddress() + " TYPE=" + reference.getReferenceType());
                    }
                }
            }
            println("SUMMARY=" + function.getEntryPoint() + " CALLS=" + calls +
                " INDIRECT=" + indirect);
        }
    }
}
