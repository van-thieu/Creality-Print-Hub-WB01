import ghidra.app.script.GhidraScript;

public class FindAvCall extends GhidraScript {
    void dump(ghidra.program.model.address.Address addr) throws Exception {
        ghidra.program.model.listing.Function f =
            currentProgram.getFunctionManager().getFunctionContaining(addr);
        if (f == null) { println("NO FUNCTION at " + addr); return; }
        println("\n===== " + f.getName() + " @ " + f.getEntryPoint() + " =====");
        ghidra.app.decompiler.DecompInterface decomp = new ghidra.app.decompiler.DecompInterface();
        decomp.openProgram(currentProgram);
        try {
            ghidra.app.decompiler.DecompileResults res = decomp.decompileFunction(f, 180, monitor);
            if (res.decompileCompleted()) println(res.getDecompiledFunction().getC());
            else println("FAILED: " + res.getErrorMessage());
        } catch (Throwable t) { println("ERROR: " + t.toString()); }
    }
    public void run() throws Exception {
        ghidra.program.model.address.AddressSpace sp =
            currentProgram.getAddressFactory().getDefaultAddressSpace();
        ghidra.program.model.address.Address target = sp.getAddress(0x4324f0L);
        ghidra.program.model.symbol.ReferenceIterator it =
            currentProgram.getReferenceManager().getReferencesTo(target);
        int n = 0;
        while (it.hasNext()) {
            ghidra.program.model.symbol.Reference r = it.next();
            ghidra.program.model.listing.Function caller =
                currentProgram.getFunctionManager().getFunctionContaining(r.getFromAddress());
            if (caller != null) {
                println("\n### CALLER at " + r.getFromAddress());
                dump(caller.getEntryPoint());
                n++;
                if (n >= 6) break;
            }
        }
        println("\nDONE callers=" + n);
    }
}
