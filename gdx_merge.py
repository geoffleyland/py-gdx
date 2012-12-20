#!/usr/bin/env python

# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxx
import gdxdict
import sys
import optparse


#- Merge two gdx files ---------------------------------------------------------

def merge_gdx(input_gdxes, output_gdx=None, gams_dir=None):
    if output_gdx == None: output_gdx = input_gdxes[1]

    G = gdxdict.gdxdict()
    for f in input_gdxes:
        G.read(f, gams_dir)

    G.write(output_gdx, gams_dir)


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage = "%prog [options] <input gdx 1> <input gdx 2> ...")
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory", default=None)
    parser.add_option("-o", "--output", help="Where to write the output file (defaults to input gdx 1)", default=None)

    try:
        options, args = parser.parse_args(argv)

        if len(args) < 3:
            parser.error("Wrong number of arguments (try python %s --help)" % args[0])

        input_gdxes = args[1:]
        output_gdx = options.output
        if not output_gdx:
            output_gdx = input_gdxes[0]

        for i in range(input_gdxes):
            if not input_gdxes[i].lower().endswith(".gdx"):
                input_gdxes[i] += ".gdx"

        print "Reading from %s and writing to '%s'" % (input_gdxes, output_gdx)
        
        merge_gdx(input_gdxes, output_gdx, options.gams_dir)

    except (optparse.OptionError, TypeError), err:
        print >>sys.stderr, err
        return 2
    except gdxx.GDX_error, err:
        print >>sys.stderr, "GDX Error: %s" % err.msg
        if err.msg == "Couldn't find the GAMS system directory":
            print "  Try specifying where GAMS is with the -g option"
        return 2
    except gdxdict.gdxdict_error, err:
        print >>sys.stderr, "Error: %s" % err.msg
        return 2

    return 1


if __name__ == "__main__":
    sys.exit(main())


#- EOF -------------------------------------------------------------------------
