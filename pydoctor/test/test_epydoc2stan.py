from __future__ import print_function

from pydoctor import epydoc2stan, model
from pydoctor.epydoc.markup import flatten
from pydoctor.sphinx import SphinxInventory
from pydoctor.test.test_astbuilder import fromText


def test_multiple_types():
    mod = fromText('''
    def f(a):
        """
        @param a: it\'s a parameter!
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class C(object):
        """
        @ivar a: it\'s an instance var
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class D(object):
        """
        @cvar a: it\'s an instance var
        @type a: a pink thing!
        @type a: no, blue! aaaargh!
        """
    class E(object):
        """
        @cvar: missing name
        @type: name still missing
        """
    ''')
    # basically "assert not fail":
    epydoc2stan.format_docstring(mod.contents['f'])
    epydoc2stan.format_docstring(mod.contents['C'])
    epydoc2stan.format_docstring(mod.contents['D'])
    epydoc2stan.format_docstring(mod.contents['E'])

def test_summary():
    mod = fromText('''
    def single_line_summary():
        """
        Lorem Ipsum

        Ipsum Lorem
        """
    def no_summary():
        """
        Foo
        Bar
        Baz
        Qux
        """
    def three_lines_summary():
        """
        Foo
        Bar
        Baz

        Lorem Ipsum
        """
    ''')
    def get_summary(func):
        stan = epydoc2stan.format_summary(mod.contents[func])
        assert stan.tagName == 'span', stan
        return flatten(stan.children)
    assert u'Lorem Ipsum' == get_summary('single_line_summary')
    assert u'Foo Bar Baz' == get_summary('three_lines_summary')
    assert u'No summary' == get_summary('no_summary')


def test_EpydocLinker_look_for_intersphinx_no_link():
    """
    Return None if inventory had no link for our markup.
    """
    system = model.System()
    target = model.Module(system, 'ignore-name')
    sut = epydoc2stan._EpydocLinker(target)

    result = sut.look_for_intersphinx('base.module')

    assert None is result


def test_EpydocLinker_look_for_intersphinx_hit():
    """
    Return the link from inventory based on first package name.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg)
    inventory._links['base.module.other'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name')
    sut = epydoc2stan._EpydocLinker(target)

    result = sut.look_for_intersphinx('base.module.other')

    assert 'http://tm.tld/some.html' == result


def test_EpydocLinker_translate_identifier_xref_intersphinx_absolute_id():
    """
    Returns the link from Sphinx inventory based on a cross reference
    ID specified in absolute dotted path and with a custom pretty text for the
    URL.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg)
    inventory._links['base.module.other'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name')
    sut = epydoc2stan._EpydocLinker(target)

    result = sut.translate_identifier_xref(
        'base.module.other', 'base.module.pretty')

    expected = (
        '<a href="http://tm.tld/some.html"><code>base.module.pretty</code></a>'
        )
    assert expected == flatten(result)


def test_EpydocLinker_translate_identifier_xref_intersphinx_relative_id():
    """
    Return the link from inventory using short names, by resolving them based
    on the imports done in the module.
    """
    system = model.System()
    inventory = SphinxInventory(system.msg)
    inventory._links['ext_package.ext_module'] = ('http://tm.tld', 'some.html')
    system.intersphinx = inventory
    target = model.Module(system, 'ignore-name')
    # Here we set up the target module as it would have this import.
    # from ext_package import ext_module
    ext_package = model.Module(system, 'ext_package')
    target.contents['ext_module'] = model.Module(
        system, 'ext_module', parent=ext_package)

    sut = epydoc2stan._EpydocLinker(target)

    # This is called for the L{ext_module<Pretty Text>} markup.
    result = sut.translate_identifier_xref(
        'ext_module', 'Pretty Text')

    expected = (
        '<a href="http://tm.tld/some.html"><code>Pretty Text</code></a>'
        )
    assert expected == flatten(result)


def test_EpydocLinker_translate_identifier_xref_intersphinx_link_not_found(capsys):
    """
    A message is sent to stdout when no link could be found for the reference,
    while returning the reference name without an A link tag.
    The message contains the full name under which the reference was resolved.
    FIXME: Use a proper logging system instead of capturing stdout.
           https://github.com/twisted/pydoctor/issues/112
    """
    system = model.System()
    target = model.Module(system, 'ignore-name')
    # Here we set up the target module as it would have this import.
    # from ext_package import ext_module
    ext_package = model.Module(system, 'ext_package')
    target.contents['ext_module'] = model.Module(
        system, 'ext_module', parent=ext_package)
    sut = epydoc2stan._EpydocLinker(target)

    # This is called for the L{ext_module} markup.
    result = sut.translate_identifier_xref(
        fullID='ext_module', prettyID='ext_module')
    assert '<code>ext_module</code>' == flatten(result)

    captured = capsys.readouterr().out
    expected = (
        "ignore-name:???: invalid ref to 'ext_module' "
        "resolved as 'ext_package.ext_module'\n"
        )
    assert expected == captured
