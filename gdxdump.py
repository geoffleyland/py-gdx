# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxcc
import gdxx
import sys
import optparse


#- Dump a GDX file to stdout ---------------------------------------------------

def dump_GDX_file(H, filename):
    assert gdxcc.gdxOpenRead(H, filename)[0], "Couldn't open %s" % filename

    info = gdxx.file_info(H)
    print "*  File Version   : %s" % info["version"]
    print "*  Producer       : %s" % info["producer"]
    print "*  Symbols        : %d" % info["symbol_count"]
    print "*  Unique Elements: %d" % info["element_count"]

    print "$ontext"
    for i in range(1, info["symbol_count"]+1):
        sinfo = gdxx.symbol_info(H, i)
        print "%-15s %3d %-12s %s" % (sinfo["name"], sinfo["dims"], sinfo["typename"], sinfo["description"])
    print "$offtext\n$onempty onembedded"

    for i in range(1, info["symbol_count"]+1):
        sinfo = gdxx.symbol_info(H, i)
        name = "%s %s" % (sinfo["full_typename"], sinfo["name"])
        dim_string = ""
        if sinfo["dims"] > 0:
            dim_string = "("
            for j in sinfo["domain"]:
                if j > 0: dim_string += ","
                d = sinfo["domain"][j]
                dim_string += d["key"]
            dim_string += ")"
        desc = sinfo["description"]
        sm = '"' if "'" in desc else "'"
        print "%s%s %s%s%s /" % (name, dim_string, sm, desc, sm)
        
        ok, records = gdxcc.gdxDataReadStrStart(H, i)
        
        for i in range(records):
            ok, elements, values, afdim = gdxcc.gdxDataReadStr(H)
            if not ok: raise GDX_error(H, "Error in gdxDataReadStr")
            if values[gdxcc.GMS_VAL_LEVEL] == 0: continue
            dim_string = ""
            for d in range(sinfo["dims"]):
                if d > 0: dim_string += "."
                dim_string += "'%s'" % elements[d]

            value_string = ""
            if sinfo["type"] == gdxcc.GMS_DT_PAR or sinfo["type"] == gdxcc.GMS_DT_VAR:
                value_string = "%g" % values[gdxcc.GMS_VAL_LEVEL]
            if sinfo["type"] == gdxcc.GMS_DT_SET:
                ret, description, node =  gdxcc.gdxGetElemText(H, int(values[gdxcc.GMS_VAL_LEVEL]))
                if ret != 0:
                    sm = '"' if "'" in description else "'"
                    value_string = "%s%s%s" % (sm, description, sm)
            print "%s %s" % (dim_string, value_string)

        print "/;\n"


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage = "%prog [options] <input gdx>")
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory", default=None)

    try:
        options, args = parser.parse_args(argv)

        if len(args) != 2:
            parser.error("Wrong number of arguments (try python %s --help)" % args[0])

        H = gdxx.open(options.gams_dir)
        dump_GDX_file(H, args[1])

    except (optparse.OptionError, TypeError), err:
        print >>sys.stderr, err
        return 2
    except gdxx.GDX_error, err:
        print >>sys.stderr, "GDX Error: %s" % err.msg
        if err.msg == "Couldn't find the GAMS system directory":
            print "  Try specifying where GAMS is with the -g option"
        return 2

    return 1


if __name__ == "__main__":
    sys.exit(main())


#- EOF -------------------------------------------------------------------------
