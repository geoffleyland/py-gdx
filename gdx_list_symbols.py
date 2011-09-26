# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxx
import gdxdict
import sys
import optparse


#- List symbols in a gdx file --------------------------------------------------

def list_symbols(files, gams_dir=None):
    G = gdxdict.gdxdict()
    for f in files:
        G.read(f, gams_dir)

    for k in G:
        info = G.getinfo(k)
        domain_string = ""
        for d in info["domain"]:
            if domain_string == "":
                domain_string = "("
            else:
                domain_string += ", "
            domain_string += d["key"]
        if domain_string != "": domain_string += ")"
        print "%s %s%s" % (info["typename"], info["name"], domain_string)


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
"""python %prog [options] <gdx file 1> <gdx file 2> ...
List all the symbols in a GDX file and their dimensions.

Examples:
python %prog days.gdx
Set days(*)
Set isweekend(days)
Parameter daynumber(days)
""")
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory if it isn't found automatically", default=None)

    try:
        options, args = parser.parse_args(argv)

        if len(args) < 2:
            parser.error("Wrong number of arguments (try python %s --help)" % args[0])

        list_symbols(args[1:], options.gams_dir)

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
