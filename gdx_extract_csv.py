#!/usr/bin/env python

# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxx
import gdxdict
import sys
import os
import os.path
import optparse
import string
import csv


#- Errors ----------------------------------------------------------------------

class extract_error(Exception):
     def __init__(self, msg):
         self.msg = msg


#- Replace a parameter with the contents of a csv file -------------------------

def write_value(v, header, values, address_map, address):
    if not address:
        if type(v) == str:
            address = (v, )
            v = True
        else:
            address = ("", )
    a = ".".join(address)
    if not a in values:
        values[a] = {}
    values[a][header] = v
    address_map[a] = address


def write_parameter(s, header, values, address_map, descriptions, stype="notset", address=None):
    if isinstance(s, gdxdict.gdxdim):
        for k in s:
            if address:
                a2 = address + (k, )
            else:
                a2 = (k, )
            if "description" in s.getinfo(k):
                a3 = ".".join(a2)
                if not a3 in descriptions:
                    descriptions[a3] = {}
                descriptions[a3][header] = s.getinfo(k)["description"]
            write_parameter(s[k], header, values, address_map, descriptions, stype, a2)
    else:
        if stype == "set": s = True
        write_value(s, header, values, address_map, address)


def write_report(filesymbols, symbols1, domains, symbol_names, output=None):
    if not output: output = sys.stdout

    # Generate all the lines for the report
    header_map = {}
    values = {}
    address_map = {}
    descriptions = {}

    for f in filesymbols:
        symbols = filesymbols[f]
        for sn in symbol_names:
            if sn in symbols:
                if len(filesymbols) > 1:
                    n, dummy = os.path.splitext(os.path.basename(f))
                    header = n + ": " + sn
                else:
                    header = sn
                header_map[header] = True
                s = symbols[sn]
                typename = symbols.getinfo(sn)["typename"]
                if typename == "Set":
                    write_parameter(s, header, values, address_map, descriptions, "set")
                else:
                    write_parameter(s, header, values, address_map, descriptions)

    uel_dict = symbols1.universal
    rows = []
    for r in values:
        names = address_map[r]
        nums = ()
        for n in names:
            if n != "":
                nums = nums + (uel_dict[n.lower()],)
            nums = nums + (1,)
        rows.append((nums, r, address_map[r]))
    rows.sort()
    headers = []
    for h in header_map: headers.append(h)
    headers.sort()

    is_one_d_set = True if (len(headers) == 1 and len(domains) == 1) else False

    csvout = csv.writer(output)

    csvrow = []
    for d in domains: csvrow.append("(" + d + ")")
    csvrow += headers
    if len(headers) == 1 and symbols1.getinfo(headers[0])["description"]:
        csvrow.append("!" + symbols1.getinfo(headers[0])["description"])
    csvout.writerow(csvrow)

    for r in rows:
        csvrow = []
        name = r[1]
        if name != "":
            csvrow += r[2]
        for h in headers:
            if name in values and h in values[name]:
                v = values[name][h]
                if type(v) == float:
                    csvrow.append("%.16g" % v)
                elif type(v) == bool:
                    if v == True:
                        csvrow.append("YES")
                    else:
                        csvrow.append("NO")
                else:
                    csvrow.append(v)
            else:
                csvrow.append("NO")
        if is_one_d_set and name in descriptions and h in descriptions[name]:
            csvrow.append(descriptions[name][h])
        csvout.writerow(csvrow)


def read_files_separately(files, gams_dir=None):
    filesymbols = {}
    symbols1 = None

    # Read all the symbols from all the files
    for f in files:
        G = gdxdict.gdxdict()
        G.read(f, gams_dir)
        filesymbols[f] = G
        if not symbols1:
            symbols1 = G
        else:
            symbols1.merge_UELs(G)

    return filesymbols, symbols1


def read_files_combined(files, gams_dir=None):
    filesymbols = {}
    symbols1 = None

    G = gdxdict.gdxdict()

    # Read all the symbols from all the files
    for f in files:
        G.read(f, gams_dir)
        if not symbols1:
            symbols1 = G
            filesymbols[f] = G

    return filesymbols, symbols1


def write_symbol_report(symbols, filesymbols, symbol_names, output=None):
    # Check the domains of all the symbols
    potential_domains = []
    for sn in symbol_names:
        for f in filesymbols:
            info = filesymbols[f].getinfo(sn)
            for d in range(info["dims"]):
                if d >= len(potential_domains):
                    pd = {}
                    potential_domains.append(pd)
                    for a in info["domain"][d]["ancestors"]:
                        if a != "*" or len(info["domain"][d]["ancestors"]) == 1:
                            if a == "*":
                                pd[a] = len(symbols.universal)
                            else:
                                pd[a] = filesymbols[f].getinfo(a)["records"]
                else:
                    pd = potential_domains[d]
                    sd = {}
                    for a in info["domain"][d]["ancestors"]:
                        if a != "*" or len(info["domain"][d]["ancestors"]) == 1:
                            if a == "*":
                                sd[a] = pd[a] = len(symbols.universal)
                            else:
                                sd[a] = filesymbols[f].getinfo(a)["records"]
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

    write_report(filesymbols, symbols, domains, symbol_names, output)


def write_domain_report(symbols, filesymbols, domains, output=None):
    possible_symbols = {}
    for f in filesymbols:
        for k in filesymbols[f]:
            possible_symbols[k] = True
        break

    # Find all the symbols that have the specified domains
    for f in filesymbols:
        symbols = filesymbols[f]
        remove = []
        for k in possible_symbols:
            if not k in symbols:
                remove.append(k)
                continue
            info = symbols.getinfo(k)
            if info["dims"] != len(domains):
                remove.append(k)
                continue
            for i in range(len(domains)):
                ok = False
                for a in info["domain"][i]["ancestors"]:
                    if a == domains[i]:
                        ok = True
                        break
                if not ok:
                    remove.append(k)
                    break

        for r in remove: del possible_symbols[r]

    symbol_names = []
    for s in possible_symbols: symbol_names.append(s)    

    write_report(filesymbols, symbols, domains, symbol_names, output)


def write_all_reports(symbols, filesymbols, output):
    try: os.makedirs(os.path.dirname(output))
    except:
        pass

    universal_file = open(output+"__universal.csv", "w")
    universal_file.write("(*)\n")
    for s in symbols.order:
        universal_file.write(s + "\n")
    universal_file.close()

    # Find all the symbols that have the specified domains
    for s in symbols:
        info = symbols.getinfo(s)
        domains = []
        for d in info["domain"]:
            domains.append(d["key"])
        write_report(filesymbols, symbols, domains, [s], open(output+s+".csv", "wb"))


#- main ------------------------------------------------------------------------

def main(argv=None):
    if argv is None:
        argv = sys.argv

    parser = optparse.OptionParser(usage =
"""python %prog [options]
Produce a csv file containing the values of selected symbols from one
or more gdx files.  Symbols can be selected by name or by selecting all the
symbols with a set of domains.

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
    parser.add_option("-i", "--index", help="Add a index (domain, dimension) to the report", action="append", dest="domains")
    parser.add_option("-c", "--compare", help="Compare symbols from all the files, rather than combining the files and reporting on the amalgamation")
    parser.add_option("-a", "--all", help="Write all symbols.  When you choose --all, you must specify an output file *prefix* with -o.  Each symbol in the gdx file will be written as a csv file named <prefix><symbol_name>.csv.  If prefix is a directory name (ie 'dir\\' on windows or 'dir/' on *nix), then any intermediate directories will be created", action="store_true")
    parser.add_option("-o", "--output", help="Where to write the output csv file (default is to the console), or the output file prefix if --all is used", default=None)
    parser.add_option("-g", "--gams-dir", help="Specify the GAMS installation directory if it isn't found automatically", default=None)

    try:
        options, args = parser.parse_args(argv)

        if not options.domains and not options.symbols and not options.all:
            parser.error("No symbols or domains specified (try python %s --help)" % args[0])

        files = options.files
        if not files: files = []
        if options.directories:
            for d in options.directories:
                for f in os.listdir(d):
                    if f.endswith(".gdx"):
                        files = files + [os.path.join(d, f)]

        for i in range(len(files)):
            if not files[i].lower().endswith(".gdx"):
                files[i] = files[i] + ".gdx"

        if len(files) == 0:
            parser.error("No files or directories specified (try python %s --help)" % args[0])

        if options.domains and options.symbols:
            print >>sys.stderr, "Both domain and symbol names specified: using domains and ignoring symbols"
        if options.all and options.symbols:
            print >>sys.stderr, "Both --all and symbol names specified: using --all"
        if options.domains and options.all:
            print >>sys.stderr, "Both domain names and --all specified: using --all"
        
        if options.all and len(files) > 1:
            raise parser.error("You can only use one input file when using --all")
        if options.all and not options.output:
            raise parser.error("You must specify an output prefix or directory when using --all")

        if options.output:
            if options.all:
                outfile = options.output
            else:
                outfile = open(options.output, "wb")
        else:
            outfile = sys.stdout

        if options.compare:
            filesymbols, symbols = read_files_separately(files, options.gams_dir)
        else:
            filesymbols, symbols = read_files_combined(files, options.gams_dir)

        if options.all:
            write_all_reports(symbols, filesymbols, outfile)
        elif options.domains:
            write_domain_report(symbols, filesymbols, options.domains, outfile)
        else:
            write_symbol_report(symbols, filesymbols, options.symbols, outfile)

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
