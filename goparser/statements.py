"statements.py -- top-level statement parser for golang"

import collections
from . import lrparser

class SyntaxError(StandardError): pass
class NotFound(StandardError): pass

class BraceScope(list):
    PAIRS = ('()', '[]', '{}')

    def __init__(self):
        super(BraceScope, self).__init__()
        self.index_stack = []

    def handle(self, i, tok):
        "if token is a brace, handle it. crash on syntax error. returns a slice if we closed a scope"
        for left, right in self.PAIRS:
            if tok.type == left:
                self.append(left)
                self.index_stack.append(i)
            elif tok.type == right:
                if self and self[-1] == left:
                    self.pop()
                    start = self.index_stack.pop()
                    return slice(start, i+1)
                else:
                    raise SyntaxError('unclosed', tok, self)

STATEMENTS = {
    tup.__name__: tup for tup in (
        collections.namedtuple('kw_func', 'method name args ret body slice'),
        collections.namedtuple('kw_type', 'name slice'),
        collections.namedtuple('kw_package', 'name slice'),
        # import var and const are processed the same way and should have the same fields
        collections.namedtuple('kw_import', 'body slice'),
        collections.namedtuple('kw_var', 'body slice'),
        collections.namedtuple('kw_const', 'body slice'),
    )
}

# this is for top-level stuff that we didn't process
NegativeSlice = collections.namedtuple('NegativeSlice', 'slice')

IGNORE = {'COMMENT1', 'COMMENTN', 'ENDL', 'WS', ' '}

def first_after(type_, istart, tokens):
    "return index of first token with type_ at or after istart in tokens"
    for i in range(istart, len(tokens)):
        if tokens[i].type == type_:
            return i
    raise NotFound(type_, istart)

def last_of(type_, tokens):
    "return index of last token with type"
    for i, tok in reversed(enumerate(tokens)):
        if tok.type == type_:
            return i
    raise NotFound(type_, None)

def add_negative_slices(tups, ntokens):
    "paste in NegativeSlice for toplevel stuff not captured so we can reassemble the file after modifying statements"
    prevstop = 0
    ret = []
    for tup in tups:
        if tup.slice.start != prevstop:
            ret.append(NegativeSlice(slice(prevstop, tup.slice.start)))
        ret.append(tup)
        prevstop = tup.slice.stop
    assert prevstop <= ntokens
    if prevstop < ntokens:
        ret.append(NegativeSlice(slice(prevstop, ntokens)))
    return ret

FUNC_PARSER = lrparser.LRParser(
    ['kw_func', ')?', 'NAME', ')', 'ret?', '}'],
    {'ret':[
        # warning: can functions return functions?
        ('kw_interface', '}'),
        (']', 'ret'),
        ('*', 'ret'),
        ('NAME', '.', 'NAME'),
        ('NAME',),
        (')',),
    ]}
)

def merge_slices(slices):
    """empty input returns empty slice. fail if slices not contiguous.
    return single slice with lowest slice.start, highest slice.stop
    """
    if not slices:
        return slice(0, 0)
    merged = slices[0]
    for slice_ in slices[1:]:
        assert slice_.start == merged.stop
        merged = slice(merged.start, slice_.stop)
    return merged

class StatementFinder:
    "see docs for parse() method"
    def __init__(self):
        self.scope = BraceScope()
        self.clear()

    def clear(self):
        "clear since-statement-open state after closing a statement"
        self.open_statement = None
        self.scopes_since_open = []
        self.slices_since_open = []

    def yield_stmts(self, tokens):
        "yield tuples from STATEMENTS for each toplevel item found in tokens"
        pairs = [(i, tok) for i, tok in enumerate(tokens) if tok.type not in IGNORE or tok.type == 'ENDL']
        for i, tok in pairs:
            closed_slice = self.scope.handle(i, tok)
            if not self.scope:
                if closed_slice is not None:
                    self.scopes_since_open.append(closed_slice)
                if self.open_statement:
                    self.slices_since_open.append(closed_slice or slice(i, i+1))
                    open_i, open_tok = self.open_statement
                    tup = STATEMENTS[open_tok.type]
                    if open_tok.type == 'kw_func':
                        if tok.type == '}':
                            if len(self.scopes_since_open) >= 2:
                                finals = [tokens[slice_.stop-1].type for slice_ in self.slices_since_open]
                                func_fields = FUNC_PARSER.parse(finals)
                                if not isinstance(func_fields, lrparser.ParseError):
                                    _, method, name, args, ret, body = [tokens[merge_slices(self.slices_since_open[slice_])] for slice_ in func_fields]
                                    yield tup(method, name, args, ret, body, slice(open_i, i+1))
                                    self.clear()
                    elif open_tok.type == 'kw_type':
                        if closed_slice is not None or tok.type == 'ENDL':
                            # note above: the condition is implicitly (ENDL && scope=0)
                            name = tokens[first_after('NAME', open_i, tokens)]
                            yield tup(name, slice(open_i, i+1))
                            self.clear()
                    elif open_tok.type == 'kw_package':
                        yield tup(tok, slice(open_i, i+1))
                        self.clear()
                    elif open_tok.type in ('kw_import', 'kw_var', 'kw_const'):
                        if closed_slice is not None or tok.type == 'ENDL':
                            yield tup(closed_slice, slice(open_i, i+1))
                            self.clear()
                    else:
                        raise ValueError('unk open_tok.type', open_tok)
                elif tok.type in STATEMENTS:
                    self.open_statement = i, tok
                    self.slices_since_open.append(slice(i, i+1))

    def parse(self, tokens):
        "return list of tuples from STATEMENTS / NegativeSlice"
        return add_negative_slices(self.yield_stmts(tokens), len(tokens))
