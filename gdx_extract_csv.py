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


def write_parameter(s, header, row_map, values, descriptions, stype="notset", address=None):
    if type(s) == dict:
        for k in s:
            if k.startswith("__"): continue
            if address:
                a2 = address + "." + k
            else:
                a2 = k
            if "__desc" in s and k in s["__desc"]:
                if not a2 in descriptions:
                    descriptions[a2] = {}
                descriptions[a2][header] = s["__desc"][k]
            write_parameter(s[k], header, row_map, values, descriptions, stype, a2)
    else:
        if stype == "set": s = True
        write_value(s, header, row_map, values, address)


def write_report(filesymbols, symbols1, domains, symbol_names, output=None):
    if not output: output = sys.stdout

    # Generate all the lines for the report
    row_map = {} 
    header_map = {}
    values = {}
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
                typename, typecode = gdxdict.get_type(symbols, sn)
                if typename == "Set":
                    write_parameter(s, header, row_map, values, descriptions, "set")
                else:
                    write_parameter(s, header, row_map, values, descriptions)

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

    is_one_d_set = True if (len(headers) == 1 and len(domains) == 1) else False

    csvout = csv.writer(output)

    csvrow = []
    for d in domains: csvrow.append("(" + d + ")")
    csvrow += headers
    if is_one_d_set:
        csvrow.append("!" + gdxdict.get_description(symbols, headers[0]))
    csvout.writerow(csvrow)

    for r in rows:
        csvrow = []
        name = r[1]
        csvrow += name.split(".")
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


def read_files(files, gams_dir=None):
    filesymbols = {}
    symbols1 = None

    # Read all the symbols from all the files
    for f in files:
        filesymbols[f] = gdxdict.read(f, gams_dir)
        if not symbols1:
            symbols1 = filesymbols[f]
        else:
            gdxdict.merge_UELs(symbols1, filesymbols[f])

    return filesymbols, symbols1


def write_symbol_report(files, symbol_names, output=None, gams_dir=None):
    filesymbols, symbols1 = read_files(files, gams_dir)

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

    write_report(filesymbols, symbols1, domains, symbol_names, output)


def write_domain_report(files, domains, output=None, gams_dir=None):
    filesymbols, symbols1 = read_files(files, gams_dir)

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
            info = gdxdict.get_symbol_info(symbols, k)
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

    write_report(filesymbols, symbols1, domains, symbol_names, output)


def write_all_reports(files, output, gams_dir=None):
    try: os.makedirs(os.path.dirname(output))
    except:
        pass
    
    filesymbols, symbols = read_files(files, gams_dir)

    universal_file = open(output+"__universal.csv", "w")
    universal_file.write("(*)\n")
    for s in symbols["__universal_order"]:
        universal_file.write(s + "\n")
    universal_file.close()

    # Find all the symbols that have the specified domains
    for s in symbols:
        if s.startswith("__"): continue
        info = gdxdict.get_symbol_info(symbols, s)
        if info["typename"] == "Scalar": continue
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
    parser.add_option("-D", "--domain", help="Add a domain to the report", action="append", dest="domains")
    parser.add_option("-a", "--all", help="Write all symbols", action="store_true")
    parser.add_option("-o", "--output", help="Where to write the output csv file (default is to the console)", default=None)
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

        if options.all:
            write_all_reports(files, outfile, options.gams_dir)
        elif options.domains:
            write_domain_report(files, options.domains, outfile, options.gams_dir)
        else:
            write_symbol_report(files, options.symbols, outfile, options.gams_dir)

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
