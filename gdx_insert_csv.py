#!/usr/bin/env python

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
        if len(domains) > 0: return # or domains[0] != "*": return
    elif stage == 2:
        if len(domains) != 1 or domains[0] != "*": return
    elif stage == 3:
        if len(domains) != 1 or domains[0] == "*": return
    else:
        if len(domains) <= 1: return

    print "Reading from", input_csv

    for d in domains:
        if d != "*":
            info = {}
            info["name"] = d
            info["dims"] = 1
            info["typename"] = "Set"
            symbols.add_symbol(info)

    for s in symbol_names:
        info = {}
        info["name"] = s
        info["dims"] = len(domains)
        info["domain"] = []
        for d in domains:
            info["domain"].append({"key": d})
        symbols.add_symbol(info)

    for row in reader:
        keys = row[0:len(domains)]
        for j in range(len(keys)):
            k = keys[j].strip()
            symbols.add_key(k)
            if domains[j] != "*":
                if not k in symbols[domains[j]]:
                    symbols[domains[j]][k] = True

        values = row[len(domains):len(domains)+len(symbol_names)]
        if len(row) > len(domains) + len(symbol_names):
            row_description = row[-1].strip()
        else:
            row_description = None
        for i in range(len(values)):
            name = symbol_names[i].strip()
            value = values[i].strip().upper()
            symbol = symbols[name]
            for j in range(len(keys)-1):
                k = keys[j].strip()
                if not k in symbol:
                    symbol[k] = gdxdict.gdxdim(symbols)
                symbol = symbol[k]

            if len(keys) == 0:
                symbol = symbols
                k = name
            else:
                k = keys[-1].strip()

            if value == "YES" or value == "NO":
                if value == "YES":
                    symbol[k] = True
                else:
                    if k in symbol: del symbol[k]
                symbols.set_type(name, "Set")
            else:
                symbol[k] = float(value)
                symbols.set_type(name, "Parameter")

            if row_description:
                symbol.setinfo(k)["description"] = row_description



    for n in symbol_names:
        name = n.strip()
        if not "typename" in symbols.getinfo(name):
            symbols.set_type(name, "Parameter")

    if description:
        symbols.setinfo(symbol_names[0])["description"] = description


def insert_symbols(input_csvs, input_gdx=None, output_gdx=None, gams_dir=None):
    if output_gdx == None: output_gdx = input_gdx

    symbols = gdxdict.gdxdict()
    if input_gdx:
        symbols.read(input_gdx, gams_dir)

    for i in range(1,5):
        for c in input_csvs:
            insert_symbol(symbols, c, i)

    symbols.write(output_gdx, gams_dir)


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
"""python %prog [options] <input csv1> [<input csv2>] ...
Insert data in a csv file into a gdx file.
""")
    parser.add_option("-i", "--input", help="Input GDX file (if omitted a new file is created)", default=None)
    parser.add_option("-o", "--output", help="Where to write the output file (defaults to overwriting input)", default=None)
    parser.add_option("-d", "--directory", help="Directory from which to read csv files", action="append", dest="directories")
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory if it isn't found automatically", default=None)

    try:
        options, args = parser.parse_args(argv)

        input_csvs = args[1:]
        input_gdx = options.input
        output_gdx = options.output
        if not output_gdx:
            if not input_gdx:
                parser.error("If you don't specify an input GDX, you must specify an output file name")
            else:
                output_gdx = input_gdx
        if options.directories:
            for d in options.directories:
                for f in os.listdir(d):
                    if f.endswith(".csv"):
                        input_csvs.append(os.path.join(d, f))

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
