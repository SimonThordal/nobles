import pytest
from hull_scraper import *
import requests_mock
import requests
import py2neo

regent_list = ['https://www.hull.ac.uk/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal05349',
'https://www.hull.ac.uk/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal05348',
'http://www.hull.ac.uk/php/cssbct/cgi-bin/gedlkup.php/n=royal?royal18704']
def custom_matcher(request):
    """
    Custom adapter to match requests to the Hull database to local files
    """
    fname = request.query
    with open('testfiles/'+fname+'.html', 'r') as fl:
        resp = requests.Response()
        resp.status_code = 200
        resp._content = fl.read()
        return resp

def test_to_path():
    with pytest.raises(Exception, message='Expecting empty path'):
        to_path('http://example.com')
    assert to_path('http://example.com/path') == '/path?'
    assert to_path('http://example.com/path?query') =='/path?query'

session = requests.session()
adapter = requests_mock.Adapter()
adapter.add_matcher(custom_matcher)
p1 = Person(regent_list[0])
p1.fetch()
p11 = Person(regent_list[0])
p11.fetch()

def test_equals():
    # People with the same URI should be equal
    assert p1 == p11

p2 = Person(regent_list[1])
p2.fetch()
def test_inequal():
    #People with different urls should not be equal
    assert p1 != p2

def test_father():
    #Father relations should be correct and relations should hold the correct path
    assert p1.parents['Father'] == p2

def test_spouse_is_list():
    #Spuses should be a list
    assert type(p2.spouses) == list

def test_mother_in_fathers_spouses():
    #My mother should be in the list of my fathers spouses
    assert p1.parents['Mother'] in p2.spouses

def children_is_list():
    # My children should be a list
    assert type(p1.children) == list

def test_marriage_to_neo():
    # to_neo should be a py2neo representation
    marriage = MarriedTo(p1, p2, {'date': 1074, 'test':True})
    assert type(marriage.to_neo()) == Relationship
    # Properties should be unpacked corectly
    assert marriage.properties['date'] == 1074

def test_child_of_to_neo():
    # to_neo should be a py2neo representation
    child_of = ChildOf(p1, p2, {'date': 1074, 'test':True})
    assert type(child_of.to_neo()) == Relationship
    # Properties should be unpacked corectly
    assert child_of.properties['date'] == 1074

def test_parent_of_to_neo():
    # to_neo should be a py2neo representation
    parent_of = ParentOf(p1, p2, {'date': 1074, 'test':True})
    assert type(parent_of.to_neo()) == Relationship
    # Properties should be unpacked corectly
    assert parent_of.properties['date'] == 1074

def test_title_of_to_neo():
    pass
