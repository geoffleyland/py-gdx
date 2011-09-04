from gdxcc import *
import sys
import os

numberParams = len(sys.argv)
if numberParams < 2 or numberParams > 3:
    print "**** Usage:", sys.argv[0], "sysDir [gdxinfn]"
    os._exit(1)
    
print sys.argv[0], "using GAMS system directory:", sys.argv[1]
    
gdxHandle = new_gdxHandle_tp()
rc =  gdxCreateD(gdxHandle, sys.argv[1], GMS_SSSIZE)
assert rc[0],rc[1]

print "Using GDX DLL version: " + gdxGetDLLVersion(gdxHandle)[1]
    
if numberParams == 2:
    assert gdxOpenWrite(gdxHandle, "demanddata.gdx", "example1")[0]
    assert gdxDataWriteStrStart(gdxHandle, "Demand", "Demand data", 1, GMS_DT_PAR , 0)

    values = doubleArray(GMS_VAL_MAX)
    
    values[GMS_VAL_LEVEL] = 324.0
    gdxDataWriteStr(gdxHandle, ["New-York"], values)
    values[GMS_VAL_LEVEL] = 299.0
    gdxDataWriteStr(gdxHandle, ["Chicago"], values)
    values[GMS_VAL_LEVEL] = 274.0
    gdxDataWriteStr(gdxHandle, ["Topeka"], values)

    assert gdxDataWriteDone(gdxHandle)
    print "Demand data written by example1"
else:
    assert gdxOpenRead(gdxHandle, sys.argv[2])[0]

    ret, fileVersion, producer = gdxFileVersion(gdxHandle)
    print "GDX file written using version: "+fileVersion
    print "GDX file written by: "+producer
        
    ret, symNr = gdxFindSymbol(gdxHandle, "x")
    assert ret, "Symbol x not found"

    ret, symName, dim, symType = gdxSymbolInfo(gdxHandle, symNr)
    assert dim == 2 and symType == GMS_DT_VAR, "**** x is not a two dimensional variable:\n" + "dim = " + str(dim) + "\nvarTyp = " + str(symType)
        
    ret, nrRecs =  gdxDataReadStrStart(gdxHandle, symNr)
    assert ret, "Error in gdxDataReadStrStart: "+gdxErrorStr(gdxHandle,gdxGetLastError(gdxHandle))[1]
        
    print "Variable x has", nrRecs, "records"
    for i in range(nrRecs):
        ret, elements, values, afdim = gdxDataReadStr(gdxHandle)
        assert ret, "Error in gdxDataReadStr: "+gdxErrorStr(gdxHandle,gdxGetLastError(gdxHandle))[1]
        if 0 == values[GMS_VAL_LEVEL]: continue
        for d in range(dim):
            print elements[d],
            if d < dim-1:
                print ".",
        print " =", values[GMS_VAL_LEVEL]
    print "All solution values shown"
    gdxDataReadDone(gdxHandle)
    
assert not gdxClose(gdxHandle)
assert gdxFree(gdxHandle)

print "All done example1"
        
