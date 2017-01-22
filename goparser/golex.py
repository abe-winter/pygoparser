"""golex.py -- tokenizer for go.
This was designed for and only tested on one file (proto/encode.go).
Enjoy with caution.
"""

import ply.lex

KEYWORDS = {k:'kw_'+k for k in 'func package return if range case default var const type struct interface'.split()}

class GoTok:
    "tokenizer for golang"
    def t_COMMENT1(self, t):
        r"//.*\n"
        # warning: what about comment on last line
        if t.value.startswith('// +build'):
            t.type = 'BUILDCONSTRAINT'
        return t

    t_COMMENTN = r"/\*(.|\n)*?\*/"
    t_ENDL = r'\n'
    t_INTLIT = r'\d+'
    t_STRLIT = r'"(\\"|.)*"'
    t_CHARLIT = r"'(\\'|\\?[^'])'"
    t_TAG = r'`[^`]+`' # todo: escaping?
    t_WS = r' \t'

    def t_NAME(self, t):
        "[A-Za-z_]\w*"
        t.type = KEYWORDS.get(t.value.lower(), 'NAME')
        return t

    def t_error(self, t):
        raise StandardError(t)

    literals = '[ ] ( ) { } , . * := : = + - != ! ; >= > <= < && || & | ^^ ^ /'
    tokens = 'NAME COMMENTN COMMENT1 ENDL INTLIT STRLIT WS BUILDCONSTRAINT CHARLIT TAG'.split() + KEYWORDS.values()

def lex(string):
    lexer = ply.lex.lex(module=GoTok())
    lexer.input(string)
    a = []
    while 1:
        t = lexer.token()
        if t:
            a.append(t)
        else:
            return a

def unlex(tokens):
    "given a list of tokens (i.e. the output of lex() above), rebuild the original string"
    return ''.join(t.value for t in tokens)
