# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxx
import gdxdict
import sys
import os
import csv
import optparse


#- Errors ----------------------------------------------------------------------

class csv_error(Exception):
     def __init__(self, msg):
         self.msg = msg


#- Replace a parameter with the contents of a csv file -------------------------

def replace_symbol(input_gdx, input_csv, symbol_name, symbol_type, description=None, output_gdx=None, gams_dir=None):
    if symbol_name == None: symbol_name, dummy = os.path.splitext(os.path.basename(input_csv))
    if output_gdx == None: output_gdx = input_gdx

    symbols = gdxdict.read(input_gdx, gams_dir)

    dims = None
    if not symbol_name in symbols:
        symbols[symbol_name] = {}
        gdxdict.set_type(symbols, symbol_name, symbol_type)
    else:
        dims = gdxdict.get_dims(symbols, symbol_name)
        typename, typecode = gdxdict.get_type(symbols, symbol_name)
        if typename != symbol_type:
            print(typename, symbol_type)
            raise gdxx.GDX_error(None, "Inconsistent symbol types")

    if description:
        gdxdict.set_description(symbols, symbol_name, desc)

    offset = 1
    if symbol_type == "Set": offset = 0

    symbol = symbols[symbol_name]
    reader = csv.reader(open(input_csv))
    for row in reader:
        current = symbol
        l = len(row)
        if dims == None:
            dims = l-offset
        elif l-offset != dims:
            raise csv_error("Inconsistent dimensions for variable")

        for c in range(l-offset):
            v = row[c]
            if c == l - offset - 1:
                if symbol_type == "Parameter":
                    current[v] = float(row[c+1])
                else:
                    current[v] = True
            else:
                if not v in current:
                    current[v] = {}
                current = current[v]

    gdxdict.set_dims(symbols, symbol_name, dims)
    gdxdict.write(symbols, output_gdx, gams_dir)


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
"""python %prog [options] <input gdx> <input csv>
Insert data in a csv file into a gdx file.
""")
    parser.add_option("-n", "--symbol-name", help="The name of the symbol to create (defaults the name of the csv file minus its suffix)", default=None)
    parser.add_option("-d", "--description", help="The description of the symbol", default=None)

    parser.set_defaults(type="Parameter")
    parser.add_option("-p", "--parameter", action="store_const", dest="type", const="Parameter", help="The symbol to be added is a parameter (default)")
    parser.add_option("-s", "--set", action="store_const", dest="type", const="Set", help="The symbol to be added is a set")

    parser.add_option("-o", "--output", help="Where to write the output file (defaults to overwriting input)", default=None)
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory if it isn't found automatically", default=None)

    try:
        options, args = parser.parse_args(argv)

        if len(args) != 3:
            parser.error("Wrong number of arguments (try python %s --help)" % args[0])

        input_gdx = args[1]
        input_csv = args[2]
        symbol_name = options.symbol_name
        if not symbol_name:
            symbol_name, dummy = os.path.splitext(os.path.basename(input_csv))
        output_gdx = options.output
        if not output_gdx:
            output_gdx = input_gdx
        symbol_type = options.type
        symbol_description = options.description
        
        print "Reading gdx from '%s', adding data in '%s' as %s '%s', and writing to '%s'" % (input_gdx, input_csv, symbol_type, symbol_name, output_gdx)
        
        replace_symbol(input_gdx, input_csv, symbol_name, symbol_type, symbol_description, output_gdx, options.gams_dir)

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
