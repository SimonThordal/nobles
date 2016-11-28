from py2neo import Graph, Relationship, Node, NodeSelector
client = Graph(password='password')

def get_parent_connections(a, b):
    """
    For two given people, A and B, get every common ancestor and the length of the path
    connecting A and B
    """

    q = """profile
        match (a:Person)-[:married_to]-(b:Person)
        where a.path = "{}"
        and b.path = "{}"
        optional match (a)-[p1:child_of *..5]->(c)<-[p2:child_of *..5]-(b)
        with size(p1) + size(p2) as path_length, c
        return distinct path_length, c"""

    return client.run(q.format(a,b))

def get_parents(person):
    q = """
        MATCH (:Person {{path: "{}"}})-[:child_of]->(b:Person)
        return distinct b
        """
    parents = client.run(q.format(person))
    return tuple(el['b']['path'] for el in parents)

def get_inbreeding_coefficient(person):
    parents = get_parents(person)
    if len(parents) > 2:
        raise Exception('{} has more than two parents'.format(person))
    if len(parents) < 2:
        return 0.0
    a,b = parents
    conns = get_parent_connections(a,b)
    return sum([1.0/2**(path['path_length']+1) for path in conns if path['path_length']])


def get_kings():
    q = 'match (t:Title) where t.name starts with "King" optional match (a)--(t) return distinct a, t'
    return client.run(q)


def get_emperors():
    q = 'match (t:Title) where t.name starts with "Emperor" optional match (a)--(t) return distinct a, t'
    return client.run(q)

def get_title(title):
    q = 'match (t:Title) where t.name starts with "{}" optional match (a)--(t) return distinct a, t'.format(title.title())
    return client.run(q)
