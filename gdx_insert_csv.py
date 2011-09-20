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

def insert_symbol(symbols, input_csv, stage):
    reader = csv.reader(open(input_csv))

    try: header = reader.next()
    except: return

    domains = []
    symbol_names = []
    description = None
    for c in header:
        c = c.strip()
        if c.startswith("("):
            domains.append(c[1:-1])
        elif c.startswith("!"):
            description = c[1:]
        else:
            symbol_names.append(c)

    if stage == 1:
        if len(domains) > 1 or domains[0] != "*": return
    elif stage == 2:
        if len(domains) > 1 or domains[0] == "*": return
    else:
        if len(domains) == 1: return

    print "Reading from", input_csv

    if description:
        gdxdict.set_description(symbols, symbol_names[0], description)

    for s in symbol_names:
        if not s in symbols:
            symbols[s] = {}
        if not "domain" in gdxdict.get_symbol_info(symbols, s):
            info = gdxdict.get_symbol_info(symbols, s)
            info["dims"] = len(domains)
            nd = []
            info["domains"] = nd
            for d in domains:
                nd.append({"key": d})
        else:
            current_domains = gdxdict.get_symbol_info(symbols, s)["domain"]
            if len(current_domains) != len(domains):
                raise csv_error("Inconsistent symbol dimensions")
            for i in range(len(domains)):
                if domains[i] != current_domains[i]["key"]:
                    raise csv_error("Inconsistent symbol dimensions")

    for row in reader:
        keys = row[0:len(domains)]
        values = row[len(domains):len(domains)+len(symbol_names)]
        if len(row) > len(domains) + len(symbol_names):
            row_description = row[-1].strip()
        else:
            row_description = None
        for i in range(len(values)):
            name = symbol_names[i].strip()
            value = values[i].strip().upper()
            symbol = symbols[name]
            for j in range(len(keys)):
                k = keys[j].strip()
                if domains[j] != "*":
                    if not domains[j] in symbols:
                        symbols[domains[j]] = {}
                        gdxdict.set_type(symbols, domains[j], "Set")
                        gdxdict.set_dims(symbols, domains[j], "*")
                    if not k in symbols[domains[j]]:
                        symbols[domains[j]][k] = True
                        gdxdict.add_UEL(symbols, k)

                if j == len(keys)-1:
                    gdxdict.add_UEL(symbols, k)
                    if value == "YES" or value == "NO":
                        if value == "YES":
                            symbol[k] = True
                        else:
                            if k in symbol: del symbol[k]
                        gdxdict.set_type(symbols, name, "Set")
                    else:
                        symbol[k] = float(value)
                        gdxdict.set_type(symbols, name, "Parameter")
                    if row_description:
                        if not "__desc" in symbol:
                            symbol["__desc"] = {}
                        symbol["__desc"][k] = row_description
                else:
                    if not k in symbol:
                        symbol[k] = {}
                    symbol = symbol[k]


def insert_symbols(input_csvs, input_gdx=None, output_gdx=None, gams_dir=None):
    if output_gdx == None: output_gdx = input_gdx

    if input_gdx:
        symbols = gdxdict.read(input_gdx, gams_dir)
    else:
        symbols = gdxdict.new()

    for c in input_csvs:
        insert_symbol(symbols, c, 1)

    for c in input_csvs:
        insert_symbol(symbols, c, 2)

    for c in input_csvs:
        insert_symbol(symbols, c, 3)

    gdxdict.write(symbols, output_gdx, gams_dir)


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
"""python %prog [options] <input csv1> [<input csv2>] ...
Insert data in a csv file into a gdx file.
""")
    parser.add_option("-i", "--input", help="Input GDX file (if ommitted a new file is created", default=None)
    parser.add_option("-o", "--output", help="Where to write the output file (defaults to overwriting input)", default=None)
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory if it isn't found automatically", default=None)

    try:
        options, args = parser.parse_args(argv)

        input_csvs = args[1:]
        input_gdx = options.input
        output_gdx = options.output
        if not output_gdx:
            if not input_gdx:
                parse.error("If you don't specify an input GDX, you must specify an output file name")
            else:
                output_gdx = input_gdx

        insert_symbols(input_csvs, input_gdx, output_gdx, options.gams_dir)

    except (optparse.OptionError, TypeError), err:
        print >>sys.stderr, err
        return 2
    except gdxx.GDX_error, err:
        print >>sys.stderr, "GDX Error: %s" % err.msg
        if err.msg == "Couldn't find the GAMS system directory":
            print "  Try specifying where GAMS is with the -g option"
        return 2
    except csv_error, err:
        print >>sys.stderr, "Error: %s" % err.msg
        return 2

    return 1


if __name__ == "__main__":
    sys.exit(main())


#- EOF -------------------------------------------------------------------------
