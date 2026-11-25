import ghidra.app.script.GhidraScript;

public class DecompFuncs extends GhidraScript {
    public void run() throws Exception {
        long[] addrs = { 0x433ddcL, 0x433dbc0L, 0x43cdfcL, 0x454538L };
        ghidra.app.decompiler.DecompInterface decomp = new ghidra.app.decompiler.DecompInterface();
        decomp.openProgram(currentProgram);
        for (long a : addrs) {
            ghidra.program.model.address.Address addr =
                currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(a);
            ghidra.program.model.listing.Function f =
                currentProgram.getFunctionManager().getFunctionContaining(addr);
            if (f == null) { println("NO FUNCTION at " + Long.toHexString(a)); continue; }
            println("\n===== " + f.getName() + " @ " + f.getEntryPoint() + " =====");
            try {
                ghidra.app.decompiler.DecompileResults res = decomp.decompileFunction(f, 180, monitor);
                if (res.decompileCompleted()) println(res.getDecompiledFunction().getC());
                else println("FAILED: " + res.getErrorMessage());
            } catch (Throwable t) { println("ERROR: " + t.toString()); }
        }
    }
}
