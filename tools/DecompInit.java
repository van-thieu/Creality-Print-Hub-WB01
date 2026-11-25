import ghidra.app.script.GhidraScript;

public class DecompInit extends GhidraScript {
    public void run() throws Exception {
        long[] addrs = { 0x434484L };
        ghidra.app.decompiler.DecompInterface decomp = new ghidra.app.decompiler.DecompInterface();
        decomp.openProgram(currentProgram);
        for (long a : addrs) {
            ghidra.program.model.address.Address addr =
                currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(a);
            ghidra.program.model.listing.Function f =
                currentProgram.getFunctionManager().getFunctionContaining(addr);
            println("\n===== " + f.getName() + " @ " + f.getEntryPoint() + " =====");
            ghidra.app.decompiler.DecompileResults res = decomp.decompileFunction(f, 180, monitor);
            if (res.decompileCompleted()) println(res.getDecompiledFunction().getC());
            else println("FAILED: " + res.getErrorMessage());
        }
    }
}
