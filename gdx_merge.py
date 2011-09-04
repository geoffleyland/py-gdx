# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxx
import gdxdict
import sys
import os
import optparse


#- Errors ----------------------------------------------------------------------

class merge_error(Exception):
     def __init__(self, msg):
         self.msg = msg


#- Merge two gdx files ---------------------------------------------------------

def traverse(d1, d2, keys=(), depth=0):
    for k in d2:
        if k.startswith("__"): continue
        v1 = None
        if k in d1: v1 = d1[k]
        v2 = d2[k]
        
        if not v1:
            d1[k] = v2
            if depth == 0:
                d1["__symbol_info"][k] = d2["__symbol_info"][k]
        else:
            if type(v1) != type(v2):
                raise merge_error("Incompatible types for " + (keys+(k,)))
            if type(v1) == dict:
                traverse(v1, v2, keys+(k,), depth+1)


def merge_gdx(input_gdx_1, input_gdx_2, output_gdx=None, gams_dir=None):
    if output_gdx == None: output_gdx = input_gdx_1

    symbols_1 = gdxdict.read(input_gdx_1, gams_dir)
    symbols_2 = gdxdict.read(input_gdx_2, gams_dir)

    traverse(symbols_1, symbols_2)

    gdxdict.write(symbols_1, output_gdx, gams_dir)


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage = "%prog [options] <input gdx 1> <input gdx 2>")
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory", default=None)
    parser.add_option("-o", "--output", help="Where to write the output file (defaults to input gdx 1)", default=None)

    try:
        options, args = parser.parse_args(argv)

        if len(args) != 3:
            parser.error("Wrong number of arguments (try python %s --help)" % args[0])

        input_gdx_1 = args[1]
        input_gdx_2 = args[2]
        output_gdx = options.output
        if not output_gdx:
            output_gdx = input_gdx_1
        
        print "Reading gdx from '%s' and '%s' and writing to '%s'" % (input_gdx_1, input_gdx_1, output_gdx)
        
        merge_gdx(input_gdx_1, input_gdx_2, output_gdx, options.gams_dir)

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
