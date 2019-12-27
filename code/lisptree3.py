#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Python port of fig's AbstractLispTree class."""
# NOTE: THIS CODE WAS WRITTEN BY ONE OF THE AUTHORS OF SEMPRE

import io

class LispTree(object):
    value = None
    children = None

    def is_leaf(self):
        return self.children is None

    def child(self, i):
        return self.children[i]

    def __getitem__(self, i):
        return self.children[i]

    def add_child(self, value):
        if isinstance(value, LispTree):
            self.children.append(value)
        else:
            self.children.append(LispTree.newLeaf(value))
        return self

    def num_leaves(self):
        if self.is_leaf():
            return 1
        n = 0
        for child in self.children:
            n += child.num_leaves()
        return n

    def num_nodes(self):
        if self.is_leaf():
            return 1
        n = 1
        for child in self.children:
            n += child.num_nodes()
        return n

    def to_list(self):
        if self.is_leaf():
            return self.value
        answer = []
        for child in self.children:
            answer.append(child.to_list())
        return answer

    @classmethod
    def new_leaf(cls, value):
        tree = cls()
        tree.value = str(value)
        return tree

    @classmethod
    def new_list(cls, *content):
        tree = cls()
        tree.children = []
        for stuff in content:
            tree.add_child(stuff)
        return tree

    ################################################
    # String --> LispTree

    @classmethod
    def parse_from_file(cls, fin):
        return list(_ParseLispTreeIterator(fin, cls))

    @classmethod
    def parse_from_string(cls, s):
        fin = io.StringIO(s)
        return list(_ParseLispTreeIterator(fin, cls))

    ################################################
    # LispTree --> String

    DEFAULT_MAX_WIDTH = 180

    def __repr__(self):
        return self.to_string_wrap()

    def to_string_wrap(self, max_width=None, sub_max_width=None):
        out = []
        self._print(out, max_width, sub_max_width)
        return ''.join(out)

    def _print(self, out, max_width=None, sub_max_width=None):
        if not max_width:
            max_width = self.DEFAULT_MAX_WIDTH
        if not sub_max_width:
            sub_max_width = max_width
        self.to_string_helper(max_width, sub_max_width, '', out)

    def num_chars(self, max_width):
        if self.is_leaf():
            return 0 if not self.value else len(self.value)
        # Add spaces and parens first
        total = 1 + len(self.children)
        for child in self.children:
            total += child.num_chars(max_width - total)
            if total >= max_width:
                break    # Break early
        return total

    def to_string_helper(self, max_width, sub_max_width, indent, out):
        if self.is_leaf():
            out.append(indent)
            if self.value is None:
                out.append('\\0')
            else:
                should_quote = (len(self.value) == 0)
                for c in self.value:
                    if c.isspace() or c in ('(', ')', '#'):
                        should_quote = True
                        break
                if should_quote:
                    out.append('"')
                for c in self.value:
                    if c in ('"', '\\'):
                        out.append('\\' + c)
                    elif c == '\n':
                        out.append('\\n')
                    elif c == '\t':
                        out.append('\\t')
                    else:
                        out.append(c)
                if should_quote:
                    out.append('"')
        else:
            # Try laying out on one line
            if self.num_chars(max_width) <= max_width:
                out.append(indent)
                out.append('(')
                first = True
                for child in self.children:
                    if not first:
                        out.append(' ')
                    child.to_string_helper(float('inf'), float('inf'), '', out)
                    first = False
                out.append(')')
            else:
                out.append(indent)
                out.append('(')
                first = True
                new_indent = indent + '  '
                for child in self.children:
                    if first and child.is_leaf():
                        child.to_string_helper(float('inf'), float('inf'), '', out)
                    else:
                        out.append('\n')
                        child.to_string_helper(sub_max_width, sub_max_width, new_indent, out)
                    first = False
                out.append('\n')
                out.append(indent)
                out.append(')')

################################################
# Iterator for parsing LispTree from stream

class _ParseLispTreeIterator(object):

    # Where we were
    start_line_num, start_i = -1, -1
    # Current line
    line_num, line = 0, None
    # Current position in line
    i = -1
    # Length of line
    n = 0
    # Current character
    c = None

    def __init__(self, fin, cls):
        self.fin = fin
        self.cls = cls
        self.advance()

    def __iter__(self):
        return self

    def __next__(self):
        self.skip_space()
        if not self.c:
            raise StopIteration
        self.start_line_num = self.line_num
        self.start_i = self.i
        return self.recurse()

    def error(self, msg):
        raise ValueError('%s from %s:%s to %s:%s' % \
                (msg, self.start_line_num, self.start_i, self.line_num, self.i))

    def advance(self):
        self.i += 1
        # If exhausted line, then go to next
        while (self.i == self.n):
            self.line = self.fin.readline()
            if not self.line:
                self.i = self.n = 0
                break
            self.line_num += 1
            self.n = len(self.line)
            self.i = 0
        self.c = None if not self.line else self.line[self.i]

    def skip_space(self):
        while self.c:
            if self.c == '#':
                # Ignore comments until end of line
                while self.c and self.c != '\n':
                    self.advance()
            elif self.c.isspace():
                # Whitespace
                self.advance()
            else:
                break

    def recurse(self):
        self.skip_space()
        if not self.c:
            return None
        elif self.c == '(':
            # List
            self.advance()
            tree = self.cls.new_list()
            while True:
                self.skip_space()
                if not self.c:
                    self.error("Missing ')'")
                elif self.c == ')':
                    self.advance()
                    break
                tree.add_child(self.recurse())
            return tree
        else:
            # Primitive
            if self.c == ')':
                self.error("Extra ')'")
            escaped, in_quote, is_null = False, False, False
            value = []
            while self.c:
                if escaped:
                    if self.c == 'n':
                        value.append('\n')
                    elif self.c == 't':
                        value.append('\t')
                    elif self.c == '0':
                        is_null = True
                    else:
                        value.append(self.c)
                    escaped = False
                elif self.c == '\\':
                    escaped = True
                elif self.c == '"':
                    in_quote = not in_quote
                else:
                    if not in_quote and (self.c.isspace() or self.c == ')'):
                        break
                    value.append(self.c)
                self.advance()
            if escaped:
                self.error('Missing escaped character')
            if in_quote:
                self.error('Missing end quote')
            return self.cls.new_leaf(None if is_null else ''.join(value))
