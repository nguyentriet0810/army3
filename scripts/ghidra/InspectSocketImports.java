// Read-only Ghidra headless script. Run on the imported GameAssembly.dll.
// It lists socket-related external symbols and a bounded set of references.

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import ghidra.program.model.symbol.Symbol;
import ghidra.program.model.symbol.SymbolIterator;

public class InspectSocketImports extends GhidraScript {
    @Override
    public void run() throws Exception {
        println("PROGRAM=" + currentProgram.getName());
        println("FUNCTION_COUNT=" + currentProgram.getFunctionManager().getFunctionCount());

        SymbolIterator symbols = currentProgram.getSymbolTable().getExternalSymbols();
        int symbolCount = 0;
        while (symbols.hasNext() && !monitor.isCancelled()) {
            Symbol symbol = symbols.next();
            String lower = symbol.getName().toLowerCase();
            if (!(lower.contains("connect") || lower.contains("recv") ||
                  lower.contains("send") || lower.contains("socket") ||
                  lower.contains("select"))) {
                continue;
            }

            symbolCount++;
            println("EXTERNAL=" + symbol.getParentNamespace().getName() +
                "::" + symbol.getName() + " @ " + symbol.getAddress());

            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(symbol.getAddress());
            int shown = 0;
            while (references.hasNext() && shown < 12) {
                Reference reference = references.next();
                Address from = reference.getFromAddress();
                Function owner = currentProgram.getFunctionManager()
                    .getFunctionContaining(from);
                println("  REF=" + from + " FUNCTION=" +
                    (owner == null ? "<unknown>" : owner.getName()));
                shown++;
            }
        }
        println("SOCKET_EXTERNAL_COUNT=" + symbolCount);
    }
}
