# Copyright (c) 2011 Incremental IP Limited
# see LICENSE for license information

import gdxcc
import gdxx
import sys
import string


#- Errors ----------------------------------------------------------------------

class gdxdict_error(Exception):
     def __init__(self, msg):
         self.msg = msg


#- Data ------------------------------------------------------------------------

level_names = [ ".l", ".m", ".lo", ".ub", ".scale" ]

type_codes = {
    "set": 0,
    "parameter": 1,
    "scalar": 1,
    "variable": 2,
    "equation": 3,
    "alias": 4,
}

def get_type_code(typename):
    return type_codes[string.lower(typename)]


GMS_SV_PINF = 3e300
GMS_SV_MINF = 4e300

default_variable_fields = [
#     .l   .m           .lo         .ub  .scale
    [ 0.0, 0.0,         0.0,         0.0, 1.0 ],    # unknown
    [ 0.0, 0.0,         0.0,         1.0, 1.0 ],    # binary
    [ 0.0, 0.0,         0.0,       100.0, 1.0 ],    # integer
    [ 0.0, 0.0,         0.0, GMS_SV_PINF, 1.0 ],    # positive
    [ 0.0, 0.0, GMS_SV_MINF,         0.0, 1.0 ],    # negative
    [ 0.0, 0.0, GMS_SV_MINF, GMS_SV_PINF, 1.0 ],    # free
    [ 0.0, 0.0,         0.0, GMS_SV_PINF, 1.0 ],    # sos1
    [ 0.0, 0.0,         0.0, GMS_SV_PINF, 1.0 ],    # sos2
    [ 0.0, 0.0,         1.0, GMS_SV_PINF, 1.0 ],    # semicont
    [ 0.0, 0.0,         1.0,       100.0, 1.0 ]     # semiint
]


#- One dimension of a gdxdict --------------------------------------------------

class gdxdim:

    def __init__(self, parent):
        self.parent = parent
        self.items = {}
        self.info = {}

    def __setitem__(self, key, value):
        self.items[key.lower()] = value
        self.parent.add_key(key)

    def __getitem__(self, key):
        return self.items[key.lower()]

    def __iter__(self):
        for k in self.parent.order:
            if k.lower() in self.items: yield k

    def __contains__(self, key):
        return key.lower() in self.items

    def getinfo(self, key, ikey=None):
        kl = key.lower()
        if kl in self.info:
            if ikey:
                return self.info[kl][ikey]
            else:
                return self.info[kl]
        else:
            if ikey:
                return None
            else:
                return {}

    def setinfo(self, key, ikey=None, value=None):
        kl = key.lower()
        if not kl in self.info:
            self.info[kl] = {}
        if ikey:
            self.info[kl][ikey] = value
        else:
            return self.info[kl]


#- Reading tools ---------------------------------------------------------------

def read_symbol(H, d, name, typename, values):
    if typename == "Set":
        d[name] = True
    else:
        d[name] = values[gdxcc.GMS_VAL_LEVEL]

    if typename == "Variable" or typename == "Equation":
        limits = {}
        for i in range(5):
            limits[level_names[i]] = values[i]
        d.setinfo(name)["limits"] = limits

    if typename == "Set":
        ret, description, node = gdxcc.gdxGetElemText(H, int(values[gdxcc.GMS_VAL_LEVEL]))
        if ret != 0:
            d.setinfo(name)["description"] = description


#- Writing Tools ---------------------------------------------------------------

values = gdxcc.doubleArray(gdxcc.GMS_VAL_MAX)


def set_symbol(H, d, name, typename, userinfo, values, dims):
    if typename == "Set":
        text_index = 0
        if "description" in d.getinfo(name):
            ret, text_index = gdxcc.gdxAddSetText(H, d.getinfo(name)["description"])
        values[gdxcc.GMS_VAL_LEVEL] = float(text_index)
    else:
        values[gdxcc.GMS_VAL_LEVEL] = d[name]

    if (typename == "Variable" or typename == "Equation") and "limits" in d.getinfo(name):
        limits = d.getinfo[name]("limits")
        for i in range(1, 5):
            ln = level_names[i]
            if ln in limits:
                values[i] = limits[ln]

    gdxcc.gdxDataWriteStr(H, dims + [name], values)


def write_symbol(H, typename, userinfo, s, dims):
    for k in s:
        s2 = s[k]
        if isinstance(s2, gdxdim):
            write_symbol(H, typename, userinfo, s2, dims + [k])
        else:
            set_symbol(H, s, k, typename, userinfo, values, dims)


#- Guessing domains ------------------------------------------------------------

def visit_domains(current, keys, dims, index):
    for k in current:
        keys[index][k] = True
        v = current[k]
        if index < dims-1:
            visit_domains(v, keys, dims, index+1)


def guess_domains(G):
    # We don't always get symbol domains from GDX (in 23.7.2 and below
    # gdxSymbolGetDomain doesn't work and otherwise, some GDX files don't seem
    # to contain this information).  So here we try to guess

    # First, find all the symbols in all the one-dimensional sets, but map
    # backwards so we have a map from every set key back to all the sets it's in
    set_map = {}
    for k in G:
        info = G.getinfo(k)
        if info["type"] == gdxcc.GMS_DT_SET and info["dims"] == 1:
            symbol = G[k]
            for e in symbol:
                if not e in set_map:
                    set_map[e] = {}
                set_map[e][k] = True

    # Then run through all the symbols trying to guess any missing domains
    for k in G:
        info = G.getinfo(k)
        if info["dims"] > 0:
            keys = [{} for i in range(info["dims"])]
            # Enumerate all the keys the symbol uses on each of its dimensions
            visit_domains(G[k], keys, info["dims"], 0)
            for i in range(info["dims"]):
                if info["domain"][i]["key"] != "*": continue
                # For each dimension that currently has '*' as it's domain,
                # work out all the possible sets
                pd = None
                for j in keys[i]:
                    if pd == None:
                        pd = {}
                        if j in set_map:
                            for s in set_map[j]: pd[s] = True
                    else:
                        remove = []
                        for s in pd:
                            if not s in set_map[j]: remove.append(s)
                        for r in remove: del pd[r]

                # If the symbol is a set itself, then we probably found that, but we don't want it
                if pd and k in pd: del pd[k]
                if pd and len(pd) > 0:
                    # If we found more than one possible set, pick the shortest
                    # one: our guess is that the set is the smallest set that
                    # contains all the keys that appear in this dimension
                    smallest_set = None
                    length = 1e9 # Can you get DBL_MAX in Python?  A billion out to be enough for anyone.
                    min_length = 0
                    # If we're working with a set, we don't want to pick a set
                    # with the exact same length - we want this to be a subset
                    # of a longer set
                    if info["type"] == gdxcc.GMS_DT_SET:
                        min_length = len(keys[i])
                    for s in pd:
                        l = G.getinfo(s)["records"]
                        if l < length and l > min_length:
                            length = l
                            smallest_set = s
                    if smallest_set:
                        info["domain"][i] = { "index":G.getinfo(smallest_set)["number"], "key":smallest_set }


def guess_ancestor_domains(G):
    for k in G:
        info = G.getinfo(k)
        if info["dims"] == 0: continue
        for i in range(info["dims"]):
            ancestors = [info["domain"][i]["key"]]
            while ancestors[-1] != '*':
                ancestors.append(G.getinfo(ancestors[-1])["domain"][0]["key"])
            info["domain"][i]["ancestors"] = ancestors


#- GDX Dict --------------------------------------------------------------------

class gdxdict:

    def __init__(self):
        self.file_info = {}

        self.universal = {}
        self.universal_info = {}
        self.order = []
        self.universal_description = []

        self.symbols = {}
        self.symbol_names = {}
        self.info = {}


    def __getitem__(self, key):
        return self.symbols[key.lower()]

    def __setitem__(self, key, value):
        self.symbols[key.lower()] = value

    def __contains__(self, key):
        return key.lower() in self.symbols

    def __iter__(self):
        seen = {}
        for stage in range(4):
            for k in self.symbols:
                info = self.getinfo(k)
                dims = info["dims"]
                domain1 = dims > 0 and info["domain"][0]["key"]
                typename = "typename" in info and info["typename"]
                if (not k in seen and
                    ((stage == 0 and typename == "Set" and dims == 1 and domain1 == "*") or
                     (stage == 1 and typename == "Set" and dims == 1 and domain1 != "*") or
                     (stage == 2 and typename == "Set" and dims > 1) or
                     (stage == 3 and typename != "Set"))):
                    for d in info["domain"]:
                        dkl = d["key"].lower()
                        if dkl != "*" and not dkl in seen:
                            yield self.symbol_names[dkl]
                            seen[dkl] = True
                    yield self.symbol_names[k]
                    seen[k] = True

    def getinfo(self, key, ikey=None):
        kl = key.lower()
        if ikey:
            return self.info[kl][ikey]
        else:
            return self.info[kl]

    def setinfo(self, key, ikey=None, value=None):
        kl = key.lower()
        if not kl in self.info:
            self.info[kl] = {}
        if ikey:
            self.info[kl] = value
        else:
            return self.info[kl]

    def add_key(self, key, description=None):
        kl = key.lower()
        if not kl in self.universal:
            self.universal[kl] = len(self.order)
            self.order.append(key)
        if description:
            self.universal_description[self.universal[kl]] = description

    def add_symbol(self, info):
        key = info["name"].lower()
        if not "type" in info and "typename" in info:
            info["type"] = get_type_code(info["typename"])
        if not "userinfo" in info:
            info["userinfo"] = 0
        if not "description" in info:
            info["description"] = ""
        
        if not key in self.info:
            self.info[key] = {}
            if info["dims"] > 0:
                self.symbols[key] = gdxdim(self)
            else:
                self.symbols[key] = None
            self.symbol_names[key] = info["name"]
        else:
            sinfo = self.info[key]
            if "type" in sinfo and "type" in info and sinfo["type"] != info["type"]:
                raise gdxdict_error("Incompatible types for symbol '%s' (%s and %s)" % (info["name"], sinfo["type"], info["type"]))
            if "dims" in sinfo and "dims" in info and sinfo["dims"] != info["dims"]:
                raise gdxdict_error("Incompatible dimensions for symbol '%s' (%d and %d)" % (info["name"], sinfo["dims"], info["dims"]))
            if "domain" in sinfo and "domain" in info:
                for d in range(len(sinfo["domain"])):
                    d1 = sinfo["domain"][d]
                    d2 = info["domain"][d]
                    if d1 and d2 and d1["key"] != d2["key"]:
                        raise gdxdict_error("Incompatible domain %d for symbol '%s' (%s and %s)" % (d, info["name"], d1["key"], d2["key"]))

        for k in info:
            if not k in self.info[key]:
                self.info[key][k] = info[k]

    def set_type(self, name, t):
        if type(t) == str:
            typename = t
            typecode = get_type_code(t)
        else:
            typecode = t
            typename = gdxx.symbol_type_text[t]
    
        info = self.setinfo(name)
        if "type" in info and info["type"] != typecode:
            raise gdxdict_error("Incompatible types for symbol '%s' (%s and %s)" % (name, info["typename"], typename))
            
        info["type"] = typecode
        info["typename"] = typename


# -- Read a gdx file -----------------------------------------------------------

    def read(self, filename, gams_dir=None):
        H = gdxx.open(gams_dir)
        assert gdxcc.gdxOpenRead(H, filename)[0], "Couldn't open %s" % filename

        info = gdxx.file_info(H)
        for k in info:
            if not k in self.file_info:
                self.file_info[k] = info[k]

        # read the universal set
        uinfo = gdxx.symbol_info(H, 0)
        for k in uinfo:
            if not k in self.universal_info: 
                self.universal_info[k] = uinfo[k]

        ok, records = gdxcc.gdxDataReadStrStart(H, 0)        
        for i in range(records):
            ok, elements, values, afdim = gdxcc.gdxDataReadStr(H)
            if not ok: raise gdxx.GDX_error(H, "Error in gdxDataReadStr")
            key = elements[0]
            ret, description, node = gdxcc.gdxGetElemText(H, int(values[gdxcc.GMS_VAL_LEVEL]))
            if ret == 0: description = None
            self.add_key(key, description)

        # Read all the other symbols
        for i in range(1, info["symbol_count"]+1):

            sinfo = gdxx.symbol_info(H, i)
            self.add_symbol(sinfo)

            ok, records = gdxcc.gdxDataReadStrStart(H, i)
        
            for i in range(records):
                ok, elements, values, afdim = gdxcc.gdxDataReadStr(H)
                if not ok: raise gdxx.GDX_error(H, "Error in gdxDataReadStr")
                if sinfo["dims"] == 0:
                    read_symbol(H, self, sinfo["name"], sinfo["typename"], values)
                else:
                    symbol = self[sinfo["name"]]
                    current = symbol
                    for d in range(sinfo["dims"]-1):
                        key = elements[d]
                        if not key in current:
                            current[key] = gdxdim(self)
                        current = current[key]
                    key = elements[sinfo["dims"]-1]
                    read_symbol(H, current, key, sinfo["typename"], values)

        gdxcc.gdxClose(H)
        gdxcc.gdxFree(H)

        guess_domains(self)
        guess_ancestor_domains(self)



#- Write a GDX file ------------------------------------------------------------

    def write(self, filename, gams_dir=None):
        H = gdxx.open(gams_dir)
        assert gdxcc.gdxOpenWrite(H, filename, "gdxdict.py")[0], "Couldn't open %s" % filename

        # write the universal set
        gdxcc.gdxUELRegisterRawStart(H)
        for i in range(len(self.order)):
            gdxcc.gdxUELRegisterRaw(H, self.order[i])
        gdxcc.gdxUELRegisterDone(H)

        for k in self:
            symbol = self[k]
            info = self.getinfo(k)
            if info["dims"] == 0:
                if not gdxcc.gdxDataWriteStrStart(H, k, info["description"], 0, get_type_code(info["typename"]), info["userinfo"]):
                    raise gdxx.GDX_error(H, "couldn't start writing data")
                set_symbol(H, self, k, info["typename"], info["userinfo"], values, [])
                gdxcc.gdxDataWriteDone(H)
            else:
                if not gdxcc.gdxDataWriteStrStart(H, k, info["description"], info["dims"], get_type_code(info["typename"]), info["userinfo"]):
                    raise gdxx.GDX_error(H, "couldn't start writing data")
                domain = []
                for d in info["domain"]:
                    domain.append(d["key"])
                if gdxcc.gdxSymbolSetDomain(H, domain) != 1:
                    raise gdxx.GDX_error(H, "couldn't set domain for symbol %s to %s" % (k, domain))
                write_symbol(H, info["typename"], info["userinfo"], symbol, [])
                gdxcc.gdxDataWriteDone(H)

        gdxcc.gdxClose(H)
        gdxcc.gdxFree(H)


#- UEL Handling ----------------------------------------------------------------

    def merge_UELs(self, G2):
        for i in range(len(G2.order)):
            self.add_key(G2.order[i], G2.universal_description[i])


#- EOF -------------------------------------------------------------------------
