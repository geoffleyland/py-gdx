# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxx
import gdxdict
import sys
import os
import optparse


#- Errors ----------------------------------------------------------------------

class extract_error(Exception):
     def __init__(self, msg):
         self.msg = msg


#- Replace a parameter with the contents of a csv file -------------------------

def are_the_last_sets_unique(s, names={}, address=None):
    assert(type(s) == dict)
    for k in s:
        if k.startswith("__"): continue
        s2 = s[k]
        if type(s2) == dict:
            if address:
                a2 = address + "." + k
            else:
                a2 = k
            count_set_elements(s[k], names, a2)
        else:
            if address in names: return False
            names[address] = True
    return True


def write_value(v, header, row_map, values, address):
    if not address:
        if type(v) == str:
            address = v
            v = True
        else:
            address = "Scalar"
    row_map[address] = True
    if not address in values:
        values[address] = {}
    values[address][header] = v


def write_set(s, header, row_map, values, address=None):
    assert(type(s) == dict)
    for k in s:
        if k.startswith("__"): continue
        s2 = s[k]
        if type(s2) == "dict":
            if address:
                a2 = address + "." + k
            else:
                a2 = k
            write_set(s[k], header, row_map, values, a2)
        else:
            write_value(k, header, row_map, values, address)


def write_parameter(s, header, row_map, values, stype="notset", address=None):
    if type(s) == dict:
        for k in s:
            if k.startswith("__"): continue
            if address:
                a2 = address + "." + k
            else:
                a2 = k
            write_parameter(s[k], header, row_map, values, stype, a2)
    else:
        if stype == "set": s = True
        write_value(s, header, row_map, values, address)


def write_report(files, symbol_names, output=None, gams_dir=None):
    if not output: output = sys.stdout

    row_map = {} 
    header_map = {}
    values = {}

    filesymbols = {}
    symbols1 = None

    # Read all the symbols from all the files
    for f in files:
        filesymbols[f] = gdxdict.read(f, gams_dir)
        if not symbols1:
            symbols1 = filesymbols[f]
        else:
            gdxdict.merge_UELs(symbols1, filesymbols[f])

    # Check the domains of all the symbols
    potential_domains = []
    for sn in symbol_names:
        for f in files:
            info = gdxdict.get_symbol_info(filesymbols[f], sn)
            for d in range(info["dims"]):
                if d >= len(potential_domains):
                    pd = {}
                    potential_domains.append(pd)
                    for a in info["domain"][d]["ancestors"]:
                        if a != "*":
                            pd[a] = gdxdict.get_symbol_info(filesymbols[f], a)["records"]
                else:
                    pd = potential_domains[d]
                    sd = {}
                    for a in info["domain"][d]["ancestors"]:
                        sd[a] = gdxdict.get_symbol_info(filesymbols[f], a)["records"]
                    remove = []
                    for a in pd:
                        if a in sd:
                            pd[a] = max(sd[a], pd[a])
                        else:
                            remove.append(a)
                    for r in remove: del pd[r]

    domains = []
    for pd in potential_domains:
        if len(pd) == 0:
            raise extract_error("Domains of the symbols do not match: you need to run the script more than once to generate more than one CSV file")
        smallest_set = None
        least = 1e9
        for s in pd:
            if pd[s] < least:
                least = pd[s]
                smallest_set = s
        domains.append(smallest_set)

    for f in files:
        symbols = filesymbols[f]
        for sn in symbol_names:
            if sn in symbols:
                if len(files) > 1:
                    n, dummy = os.path.splitext(os.path.basename(f))
                    header = n + ": " + sn
                else:
                    header = sn
                header_map[header] = True
                s = symbols[sn]
                typename, typecode = gdxdict.get_type(symbols, sn)
                if typename == "Set":
                    if gdxdict.get_dims(symbols, sn) > 1 and are_the_last_sets_unique(s):
                        write_set(s, header, row_map, values)
                    else:
                        write_parameter(s, header, row_map, values, "set")
                else:
                    write_parameter(s, header, row_map, values)

    uel_dict = symbols1["__universal_dict"]
    rows = []
    for r in row_map:
        names = r.split(".")
        nums = ()
        for n in names:
            nums = nums + (uel_dict[n],)
        rows.append((nums, r))
    rows.sort()
    headers = []
    for h in header_map: headers.append(h)
    headers.sort()
    
    output.write("Key")
    for h in headers: output.write(", %s" % h)
    output.write("\n")
    for r in rows:
        name = r[1]
        output.write(name)
        for h in headers:
            output.write(", ")
            if name in values and h in values[name]:
                v = values[name][h]
                if type(v) == float:
                    output.write("%g" % v)
                elif type(v) == bool:
                    if v == True:
                        output.write("X")
                else:
                    output.write(v)
        output.write("\n")


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
"""python %prog [options]
Produce a csv file containing the values of selected sets or parameters from one
or more gdx files.

Examples:
python %prog -f days.gdx -s daynumber -s isweekend
Key, daynumber, isweekend
Monday, 1,
Tuesday, 2,
...
Saturday, 6, X
Sunday, 7, X

python %prog -f gdp_1973.gdx -f gdp_2003.gdx -s gdp
Key, gdp_1973: gdp, gdp_2003: gdp
Austria, 82227, 173311
Belgium, 118526, 219069
Denmark, 70032, 124781
""")
    parser.add_option("-f", "--file", help="Add a gdx file to read from", action="append", dest="files")
    parser.add_option("-d", "--directory", help="Add a directory to read several gdx files from", action="append", dest="directories")
    parser.add_option("-s", "--symbol", help="Add a symbol to the report", action="append", dest="symbols")
    parser.add_option("-o", "--output", help="Where to write the output csv file (default is to the console)", default=None)
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory if it isn't found automatically", default=None)

    try:
        options, args = parser.parse_args(argv)

        if not options.symbols:
            parser.error("No symbols specified (try python %s --help)" % args[0])

        files = options.files
        if not files: files = []
        if options.directories:
            for d in options.directories:
                for f in os.listdir(d):
                    if f.endswith(".gdx"):
                        files = files + [os.path.join(d, f)]

        if len(files) == 0:
            parser.error("No files or directories specified (try python %s --help)" % args[0])

        if options.output:
            outfile = open(options.output, "w")
        else:
            outfile = sys.stdout

        write_report(files, options.symbols, outfile, options.gams_dir)

    except (optparse.OptionError, TypeError), err:
        print >>sys.stderr, err
        return 2
    except gdxx.GDX_error, err:
        print >>sys.stderr, "GDX Error: %s" % err.msg
        if err.msg == "Couldn't find the GAMS system directory":
            print "  Try specifying where GAMS is with the -g option"
        return 2
    except extract_error, err:
        print >>sys.stderr, "Error: %s" % err.msg
        return 2

    return 1


if __name__ == "__main__":
    sys.exit(main())


#- EOF -------------------------------------------------------------------------
