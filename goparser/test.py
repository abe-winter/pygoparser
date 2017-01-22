import pytest, os, shutil
from . import golex, lrparser, statements

FNAME = os.path.join(os.path.dirname(__file__), 'encode.go')

def test_golex():
    orig = open(FNAME).read()
    tokens = golex.lex(orig)
    assert golex.unlex(tokens) == orig

def test_lrparser():
    from .lrparser import ParseError
    p = lrparser.LRParser(
        ['func', ')?', 'name', 'ret?', '}'],
        {'ret': [
            (']', 'ret'),
            ('name',),
            ('interface', '}'),
        ]}
    )
    assert ParseError(0, p.spec[0], 0) == p.parse(['must', 'start', 'with', 'func'])
    assert [slice(0, 1), slice(1, 1), slice(1, 2), slice(2, 2), slice(2, 3)] == p.parse(['func', 'name', '}'])
    # make sure specials and literals aren't confused
    assert ParseError(2, p.spec[4], 4) == p.parse(['func', 'name', 'ret'])
    # incomplete
    assert ParseError(4, p.spec[4], 4) == p.parse(['func', 'name', 'interface', '}'])
    assert [slice(0, 1), slice(1, 1), slice(1, 2), slice(2, 4), slice(4, 5)] == p.parse(['func', 'name', 'interface', '}', '}'])
    assert [slice(0, 1), slice(1, 1), slice(1, 2), slice(2, 5), slice(5, 6)] == p.parse(['func', 'name', ']', 'interface', '}', '}']) # recursion
    assert [slice(0, 1), slice(1, 1), slice(1, 2), slice(2, 5), slice(5, 6)] == p.parse(['func', 'name', ']', ']', 'name', '}']) # recursion
    assert [slice(0, 1), slice(1, 2), slice(2, 3), slice(3, 3), slice(3, 4)] == p.parse(['func', ')', 'name', '}'])

def test_statements():
    tokens = golex.lex(open(FNAME).read())
    stmts = statements.StatementFinder().parse(tokens)
    assert sum((tokens[tup.slice] for tup in stmts), []) == tokens

@pytest.mark.skip
def test_toplevel_edge_cases():
    "this shows cases where the toplevel parser may fail. todo: run this and fix if needed"

    source = 'package /*comment*/ name'
    source = "func (self *C) F() []byte {}"
    source = "func (self *C) F() interface{} {}"
    source = "var name =\n3"
    source = "func F() *Pointer {}"
    source = "func F() *pkg.Pointer {}"
    source = "func F() []*pkg.Pointer {}"

    raise NotImplementedError
