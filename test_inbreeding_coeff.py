from inbreeding_coef import *

# There can be multiple ways of connecting two people in the graph, so a list should be returned
def returns_list():
    pass

# Marie Louise, princess of Denmark
ml = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal01655"
# Parents of ml
frede = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal01617"
marie = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal01618"
# Common ancestors of frede and marie
louisa = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal00331"
frederik = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal00344"
wilhelmina = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal00322"
george = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal00321"
# Aslaug has only one parent
aslaug = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal14301"
# Sigurd has no parents
sigurd = "/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal14302"


def test_get_parents():
    # frede and marie are the parents of ml
    a, b = get_parents(ml)
    assert set([a,b]) - set([frede, marie]) == set()
    parents = list(get_parents(aslaug))
    assert len(parents) == 1
    parents = list(get_parents(sigurd))
    assert len(parents) == 0

def test_get_parent_connections():
    conns = list(get_parent_connections(frede, marie))
    assert len(conns) == 4
    for con in conns:
        if con['c']['path'] == louisa:
            assert con['path_length'] == 4
        elif con['c']['path'] == frederik:
            assert con['path_length'] == 4
        elif con['c']['path'] == wilhelmina:
            assert con['path_length'] == 6
        elif con['c']['path'] == george:
            assert con['path_length'] == 6

def test_get_inbreeding_coefficient():
    # frede and marie are first cousins, so their children should have an
    # inbreeding coef of 2/32 from this. They are however
    # (http://www.genetic-genealogy.co.uk/Toc115570144.html)
    ic = get_inbreeding_coefficient(ml)
    assert ic == 1.0/16+1.0/64
    assert get_inbreeding_coefficient(aslaug) == 0.0
    assert get_inbreeding_coefficient(sigurd) == 0.0
