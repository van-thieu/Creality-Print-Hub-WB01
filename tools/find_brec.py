# Ghidra headless post-script: find xrefs to the "brec:%d" format string and decompile callers.
from ghidra.app.decompiler import DecompInterface
from ghidra.util.task import ConsoleTaskMonitor

addr = currentProgram.getAddressFactory().getDefaultAddressSpace().getAddress(0x771ca4)
refs = currentProgram.getReferenceManager().getReferencesTo(addr)
print("BREC XREFS: %d" % len(refs))
seen = set()
decomp = DecompInterface()
decomp.openProgram(currentProgram)
for ref in refs:
    f = currentProgram.getFunctionManager().getFunctionContaining(ref.getFromAddress())
    if f is None or f.getEntryPoint() in seen:
        continue
    seen.add(f.getEntryPoint())
    print("\n===== FUNCTION %s @ %s =====" % (f.getName(), f.getEntryPoint()))
    res = decomp.decompileFunction(f, 180, ConsoleTaskMonitor())
    if res.decompileCompleted():
        print(res.getDecompiledFunction().getC())
    else:
        print("DECOMPILE FAILED: %s" % res.getErrorMessage())
