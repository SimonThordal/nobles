import requests as req
import BeautifulSoup as bs
from urlparse import urljoin, urlsplit
from collections import deque
import datetime
import re
from py2neo import Graph, Relationship, Node, NodeSelector
import dateparser as dp
import time
import settings_module as settings

root = settings.ROOT
master_list = "/php/cssbct/cgi-bin/gedidex.php/n=royal?denmark"
session = req.Session()
a = req.adapters.HTTPAdapter(max_retries=3)
session.mount('http://', a)
client = Graph(password =s ettings.NEO_PASSWORD)

def get_regent_list():
    # Send back the cookie
    resp = session.get(root+master_list)
    if not resp.status_code == 200:
        raise Exception('Response of {} failed with status {} \n\n Content: {}'.format(master_list, resp.status_code, resp.text))
    jar = resp.cookies
    regent_list = session.get(root+master_list, cookies=jar)
    if not regent_list.status_code == 200:
        raise Exception('Cookie authenticated response of {} failed with status {} \n\n Content: {}'.format(master_list, regent_list.status_code, regent_list.text))
    soup = bs.BeautifulSoup(regent_list.content)
    # Turn the html into a list of links
    regent_list = [el.find('a').get('href') for el in soup.findAll('dt')]
    return regent_list

def get_unfinished_person():
    crs = client.run("match (a:Person) where not exists(a._cat) return a limit 1")
    return crs.next()['a']

def to_path(url):
    """ Returns the path and query for a given url"""
    split = urlsplit(url)
    path =  split.path + '?' + split.query
    if path == '?':
        raise Exception('Empty path found')
    return path

def parse_date(date_string):
    """ Parse a date string of the format 15 JUN 1902"""
    date_pat = re.compile(r'(?P<date>\d+)*?\s*(?P<month>JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)?\s*(?P<year>\d{3,4})')
    date = re.search(date_pat, date_string).groupdict()
    # Pad years < 1000 as dateparse otherwise cannot parse them
    date['year'] = "0"*(4-len(date['year'])) + date['year']
    date = dp.parse(" ".join([val if val else "01" for val in date.values()]))
    return date.year, str(date.date())

class Loggable():

    def __init__(self, id):
        self.id = id

    def log(self, message):
        with open('logs.txt', 'a') as fl:
            fl.write(str(datetime.datetime.now().isoformat()) + "{}: {}\n".format(self.id, message))

class Persistable():

    def __init__(self, caller):
        self.caller = caller

    def persist(self):
        """
        Persist this to neo4j
        """
        neo = self.caller.to_neo()
        client.merge(neo)
        neo.update(self.caller.props)
        client.push(neo)

    def is_persisted(self):
        """
        Check if this already is persisted to neo4j
        TODO: Make code less hateable
        """
        neo = self.caller.to_neo()
        label = list(neo.labels())[0]
        neo.update(self.caller.props)
        selector = NodeSelector(client)
        return len(list(selector.select(label, **dict(neo)))) > 0

class Person():

    def __init__(self, url):
        self.root = "http://www.hull.ac.uk"
        self.path = to_path(url)
        self.log = Loggable(self.path).log
        self.persist = Persistable(self).persist
        self.is_persisted = Persistable(self).is_persisted
        self.props = {'_cat':True}

    def __eq__(self, other):
        if isinstance(other, Person):
            return self.path == other.path
        return self.path == other

    def fetch(self):
        """
        Populate person from the Hull database
        """
        soup = self.__get_person_doc()
        # We do not know what properties will exist for a given character, so set it as a dict

        self.props.update(self.__get_person_properties(soup))

        self.children = self.__get_children(soup)
        self.parents = self.__get_parents(soup)
        self.marriages = self.__get_marriages(soup)
        self.spouses = [spouse for spouse, _ in self.marriages]

    def to_neo(self):
        """
        Return a neo4j representaion of this node
        """
        return Node("Person", path=self.path)


    def __get_person_doc(self):
        """ Get a BeautifulSoup representaion of a document for a specific person"""
        headers = {'user-agent': 'royalty-bot/0.0.1'}
        resp = session.get(urljoin(self.root, self.path), timeout=5, headers=headers)
        if not resp.status_code == 200:
            raise req.exceptions.ConnectionError('Response of {} failed with status {} \n\n Content: {}'.format(self.path, resp.status_code, resp.text))
        return bs.BeautifulSoup(resp.content)

    def __get_person_properties(self, soup):
        """ Get a dict of all the basic properties of an entry
        return:
        props -- dict of properties, none guaranteed to be there
        """
        try:
            name_string = soup.find('h2').text
            props = self.__parse_title_string(name_string)
            try:
                self.log(props['log_message'])
                del props['log_message']
            except KeyError:
                pass
        except:
            self.log("error parsing h2 tag.")
            props = {}


        # Get the date based properties
        props_to_find = ['Born', 'Acceded', 'Died']
        for prop in props_to_find:
            tag = soup.find(text=prop)
            if tag:
                try:
                    year, date_string = parse_date(tag.parent.nextSibling)
                    props[prop+'_year'] = year
                    props[prop] = date_string
                except:
                    pass
                    self.log('Error in recovering {} property'.format(prop))
        return props

    def __get_marriages(self, soup):
        """
        Return the marriages for the person as a list of tuples of (path, date of marriage)
        """
        def parse_marriage(marriage):
            """
            Find the path of the spouse and possibly the date of marriages
            arguments:
            marriage -- BeautifulSoup navigable string
            """
            try:
                to = to_path(marriage.findNext('a').get('href'))
            except AttributeError:
                self.log('Error parsing marriage: {}'.format(str(marriage)))
                to = None

            # Parse date using the dateparse module
            year = None
            date_string = None
            try:
                year, date_string = parse_date(marriage.next)
            except AttributeError:
                pass
            except TypeError:
                self.log("Date found while parsing marriage, but dateparse could not parse it")

            return (to, {'date': date_string, 'year': year})

        return [parse_marriage(marriage) for marriage in soup.findAll(text='Married')]

    def __get_children(self, soup):
        """Return the paths of children contained in a document about a person"""
        # Extract the hrefs of the children from the DOM
        try:
            child_els = [el.parent.nextSibling.nextSibling.get('href') for el in soup.findAll(text='Child')]
            # Ensure that only the path of the url is returned
            child_els = [to_path(child) for child in child_els]
        except AttributeError:
            child_els  = []
        return child_els

    def __parse_title_string(self, s):
        """
        Returns name, string and title of based on the input.
        Arguments:
        s -- string formatted as FAMILY, NAME, TITLE as per Hull DB standard
        returns:
        res -- dict of properties contained in s, along with possible log message
        """
        res = {}
        arr = s.split(',')
        # Assumed case as extraneous information sometimes is added to the end of the string
        if len(arr) >= 3:
            res['Family'] = arr[0].strip()
            res['Name'] = arr[1].strip()
            res['Title'] = arr[2].strip()
        # We're assuming title might be left out here
        if len(arr) == 2:
            res['Family'] = arr[0].strip()
            res['Name'] = arr[1].strip()
        # Most probably the name will be in string
        if len(arr) == 1:
            res['Name'] = arr[0].strip()

        return res

    def __get_parents(self, soup):
        """
        Return a link to the parents
        """
        # Father and mother tags are not navigable, so we'll need to find them in the list of paragraphs
        ps = soup.findAll('p')
        parents = {}
        for i,p in enumerate(ps):
            if p.text.lower().find('father') != -1:
                father = p.find('a')
                parents['Father'] = to_path(father.get('href'))
            if p.text.lower().find('mother') != -1:
                mother = p.find('a')
                parents['Mother'] = to_path(mother.get('href'))
        return parents

    def get_persisted(self):
        """
        Return persisted version
        """
        query = "MATCH (a) WHERE a.path = '{}' RETURN a LIMIT 1"
        match = client.data(query)
        if len(match) == 0:
            return None
        else:
            return match[0]


class Relation():
    def __init__(self, source, target, props={}):
        if isinstance(source, Person):
            self.source = source.path
        else:
            self.source = source
        if isinstance(target, Person):
            self.target = target.path
        else:
            self.target = target

        self.props = props
        self.persist = Persistable(self).persist
        self.is_persisted = Persistable(self).is_persisted



class MarriedTo(Relation):

    def to_neo(self):
        return Relationship(Node('Person', path=self.source), 'married_to', Node('Person', path=self.target), **self.props)

class ChildOf(Relation):

    def to_neo(self):
        return Relationship(Node('Person', path=self.source), 'child_of', Node('Person', path=self.target))


class ParentOf(Relation):

    def to_neo(self):
        return Relationship(Node('Person', path=self.source), 'parent_of', Node('Person', path=self.target))

class HoldsTitle(Relation):
    def to_neo(self):
        return Relationship(Node('Person', path=self.source), 'holds_title', Node('Title', name=self.target), **self.props)


def graph_search(start_node_path, limit=float('Inf')):
    """
    Exchaustively search the genealogical tree in a way that lets us record
    the type of relationship between nodes
    """

    stack = []
    count = 0
    get_frequency = 5
    time.sleep(get_frequency)
    try:
        node = Person(start_node_path)
        if not node.is_persisted():
            try:
                node.fetch()
            except (req.exceptions.ConnectionError, req.exceptions.ConnectTimeout) as e:
                node.log(e.message)
                return
            node.persist()
            t1 = time.time()

            for spouse, props in node.marriages:
                MarriedTo(node, spouse, props).persist()
                stack.append(spouse)

            for child in node.children:
                ParentOf(node, child).persist()
                stack.append(child)

            for parent in node.parents.values():
                ChildOf(node, parent).persist()
                stack.append(parent)

            if node.props.has_key('Title'):
                title = node.props['Title']
                props = {}
                if node.props.has_key('Acceded'):
                    props['acceded'] = node.props['Acceded']
                    props['acceded_year'] = node.props['Acceded_year']
                HoldsTitle(node, title, props).persist()

        while len(stack) > 0 and count <= limit:
            if count % 20 == 0:
                print "Processed nodes: {}\nLength of stack: {}".format(count, len(stack))
            node = Person(stack.pop())
            if not node.is_persisted():
                time_elapsed = time.time() - t1
                if time_elapsed < get_frequency:
                    time.sleep(get_frequency - time_elapsed)
                    try:
                        node.fetch()
                    except (req.exceptions.ConnectionError, req.exceptions.ConnectTimeout) as e:
                        node.log(e.message)
                        break
                node.persist()
                t1 = time.time()
                for spouse, props in node.marriages:
                    MarriedTo(node, spouse, props).persist()
                    stack.append(spouse)

                for child in node.children:
                    ParentOf(node, child).persist()
                    stack.append(child)

                for parent in node.parents.values():
                    ChildOf(node, parent).persist()
                    stack.append(parent)

                if node.props.has_key('Title'):
                    title = node.props['Title']
                    props = {}
                    if node.props.has_key('Acceded'):
                        props['acceded'] = node.props['Acceded']
                        props['acceded_year'] = node.props['Acceded_year']
                    HoldsTitle(node, title, props).persist()

                count += 1
    except Exception as e:
        node.log(e.message)
        raise e

    return (stack, count)
