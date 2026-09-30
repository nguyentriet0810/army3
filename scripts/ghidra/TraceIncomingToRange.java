// Read-only reverse call-graph trace from a target to callers in an address range.
// Usage: -postScript TraceIncomingToRange.java TARGET RANGE_START RANGE_END [MAX_DEPTH]

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.ReferenceIterator;
import java.util.*;

public class TraceIncomingToRange extends GhidraScript {
    private static class Node {
        final Function function;
        final int depth;
        final String chain;

        Node(Function function, int depth, String chain) {
            this.function = function;
            this.depth = depth;
            this.chain = chain;
        }
    }

    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        if (args.length < 3) {
            throw new IllegalArgumentException(
                "Pass target, range start/end, and optional max depth");
        }

        Address targetAddress = parse(args[0]);
        Address rangeStart = parse(args[1]);
        Address rangeEnd = parse(args[2]);
        int maxDepth = args.length > 3 ? Integer.parseInt(args[3]) : 5;
        Function target = currentProgram.getFunctionManager()
            .getFunctionContaining(targetAddress);
        if (target == null) {
            throw new IllegalArgumentException("No function contains target " + targetAddress);
        }

        ArrayDeque<Node> queue = new ArrayDeque<>();
        HashMap<Address, Integer> bestDepth = new HashMap<>();
        queue.add(new Node(target, 0, target.getEntryPoint().toString()));
        bestDepth.put(target.getEntryPoint(), 0);
        int rangeHits = 0;
        int traversedEdges = 0;

        while (!queue.isEmpty() && !monitor.isCancelled()) {
            Node node = queue.removeFirst();
            if (node.depth >= maxDepth) continue;

            ReferenceIterator references = currentProgram.getReferenceManager()
                .getReferencesTo(node.function.getEntryPoint());
            while (references.hasNext() && !monitor.isCancelled()) {
                Reference reference = references.next();
                if (!reference.getReferenceType().isCall()) continue;
                Function caller = currentProgram.getFunctionManager()
                    .getFunctionContaining(reference.getFromAddress());
                if (caller == null || caller.equals(node.function)) continue;
                traversedEdges++;
                String chain = reference.getFromAddress() + "->" + node.chain;

                if (inside(reference.getFromAddress(), rangeStart, rangeEnd)) {
                    println("RANGE_CALLSITE=" + reference.getFromAddress() +
                        " DEPTH=" + (node.depth + 1) + " CALLER=" +
                        caller.getName() + "@" + caller.getEntryPoint() +
                        " CHAIN=" + chain);
                    rangeHits++;
                    continue;
                }

                int nextDepth = node.depth + 1;
                Integer previous = bestDepth.get(caller.getEntryPoint());
                if (previous != null && previous <= nextDepth) continue;
                bestDepth.put(caller.getEntryPoint(), nextDepth);
                queue.addLast(new Node(caller, nextDepth,
                    caller.getEntryPoint() + "->" + node.chain));
            }
        }

        println("SUMMARY TARGET=" + target.getEntryPoint() + " MAX_DEPTH=" +
            maxDepth + " FUNCTIONS=" + bestDepth.size() + " EDGES=" +
            traversedEdges + " RANGE_HITS=" + rangeHits);
    }

    private Address parse(String value) throws Exception {
        return currentProgram.getAddressFactory().getDefaultAddressSpace()
            .getAddress(value);
    }

    private boolean inside(Address address, Address start, Address end) {
        return address.compareTo(start) >= 0 && address.compareTo(end) < 0;
    }
}
