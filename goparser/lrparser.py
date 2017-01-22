"lrparser -- simple & underpowered LR parser"

import collections

SpecToken = collections.namedtuple('SpecToken', 'name optional')
Match = collections.namedtuple('Match', 'spec_index matched_len')
ParseError = collections.namedtuple('ParseError', 'nconsumed unsat_spec unsat_i')

def parse_spec(elt):
    return SpecToken((elt[:-1] if elt[-1]=='?' else elt), elt[-1] == '?')

class Cursor:
    def __init__(self, tokens, i=0):
        self.tokens = tokens
        self.i = i

    def consume(self, n, label=None):
        if self.i + n > len(self.tokens):
            raise IndexError('%i + %i > %i' % (self.i, n, len(self.tokens)))
        self.i += n

    def copy(self):
        return Cursor(self.tokens, self.i)

    def __sub__(self, other):
        return self.i - other.i

    def __len__(self):
        return len(self.tokens)

    def peek(self):
        return self.tokens[self.i]

class LRParser:
    def __init__(self, spec, specials):
        """spec: list of strings representing either tok_types or keys in specials
        specials: {name: forms} for composite elements. Can be recursive.
        """
        # todo: pass in 'optional' marker and default to '?'
        assert len(spec)
        self.spec = map(parse_spec, spec)
        self.specials = {
            name: [map(parse_spec, row) for row in rows]
            for name, rows in specials.items()
        }

    def match(self, stoken, cursor):
        "returns integer length of match if success, else None. Careful: 0 means success, None means failure."
        if stoken.name in self.specials:
            for row in self.specials[stoken.name]:
                nmatched = self.match_row(row, cursor)
                if nmatched is not None:
                    return nmatched
            return 0 if stoken.optional else None
        else:
            return 1 if cursor.i < len(cursor) and stoken.name == cursor.peek() else 0 if stoken.optional else None

    def match_row(self, stokens, cursor):
        row_cursor = cursor.copy()
        for itok in stokens:
            nmatched = self.match(itok, row_cursor)
            if nmatched is None:
                return None
            else:
                row_cursor.consume(nmatched)
        return row_cursor - cursor

    def parse(self, tokens):
        """return list with same length as self.spec.
        Each element will be a slice (slices can have len=0 for optional fields).
        return ParseError tuple with details if parse failed.
        """
        cursor = Cursor(tokens)
        ret = []
        for i, stok in enumerate(self.spec):
            nmatched = self.match(stok, cursor)
            if nmatched is None:
                return ParseError(cursor.i, stok, i)
            else:
                ret.append(slice(cursor.i, cursor.i+nmatched))
                cursor.consume(nmatched)
        return ret
