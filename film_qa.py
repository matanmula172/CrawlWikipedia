import re
import requests
import lxml.html
import rdflib
import sys

URL = "https://en.wikipedia.org/wiki/List_of_Academy_Award-winning_films"
WIKI_PREFIX = "https://en.wikipedia.org"
EXAMPLE_PREFIX = "http://example.org"
ONTOLOGY_NAME = 'ontology.nt'
INFOBOX_VEVENT_PREFIX = "//table[contains(@class, 'infobox vevent')]"
INFOBOX_BIOGRAPHY_PREFIX = "//table[contains(@class, 'infobox biography')]"

"""
This function gets a document (a web page) and a relation (Release date)
 and returns all the entities relevant to this relation
 :parameter doc (html document)
 :parameter relation (string)
 :return entity_lst (list)
"""


def get_release_date(doc, relation):
    entity_lst = doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'"
                           + relation + "')]//ancestor-or-self::th""/../td//"
                                        "span[contains(@class, 'bday')]//text()")
    if not entity_lst:
        entity_lst = list()
        poss_entities = doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'"
                                  + relation + "')]//ancestor-or-self::th""/../td//text()")
        for ent in poss_entities:
            poss_year = str(ent).split()
            for s in poss_year:
                if s.isnumeric() and len(s) == 4:
                    entity_lst.append(s)
    return entity_lst


"""
This function gets a document (a web page) and a relation (Born)
 and returns all the entities relevant to this relation
 :parameter doc (html document)
 :parameter relation (string)
 :return entity_lst (list)
"""


def get_bday(doc, relation):
    # check if exists text in bday tag
    entity_lst = doc.xpath(INFOBOX_BIOGRAPHY_PREFIX + "//*[contains(text(),'"
                           + relation + "')]//ancestor-or-self::th""/../td//"
                                        "span[contains(@class, 'bday')]//text()")

    # if not, get year
    if not entity_lst:
        entity_lst = doc.xpath(INFOBOX_BIOGRAPHY_PREFIX + "//*[contains(text(),'"
                               + relation + "')]//ancestor-or-self::th""/../td//text()")
        entity_lst = [str(entity_lst[0]).split('/')]
        if entity_lst:
            entity_lst = entity_lst[0]
    return entity_lst


"""
This function gets a document (a web page) and a relation (Occupation)
 and returns all the entities relevant to this relation
 :parameter doc (html document)
 :parameter relation (string)
 :return entity_lst (list)
"""


def get_occupation(doc, relation):
    pos_entity_lst = doc.xpath(INFOBOX_BIOGRAPHY_PREFIX + "//*[contains(text(),'"
                               + relation + "')]//ancestor-or-self::th""/../td//text()")
    entity_lst = []
    for i in range(len(pos_entity_lst)):
        occ_lst = str(pos_entity_lst[i]).split(',')
        for j in range(len(occ_lst)):
            inner_occ_lst = str(occ_lst[j]).split('and')
            for k in range(len(inner_occ_lst)):
                inner_occ_lst[k] = inner_occ_lst[k].strip().lower()
                entity_lst.append(inner_occ_lst[k])
    return entity_lst


"""
This function gets a document (a web page) and a relation (Running time)
 and returns all the entities relevant to this relation
 :parameter doc (html document)
 :parameter relation (string)
 :return entity_lst (list)
"""


def get_running_time(doc, relation):
    # check if exists text in li tag
    entity_lst = doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'"
                           + relation + "')]//ancestor-or-self::th""/../td//"
                                        "li/text()")
    if not entity_lst:
        entity_lst = doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'"
                               + relation + "')]//ancestor-or-self::th""/../td//text()")
    return entity_lst


"""
This function gets a document (a web page) and a relation (Based on)
 and returns all the entities relevant to this relation
 :parameter doc (html document)
 :parameter relation (string)
 :return entity_lst (list)
"""


def get_based_on(doc, relation):
    entity_lst = doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'"
                           + relation + "')]//ancestor-or-self::th""/../td//text()")

    entity = (" ".join(entity_lst)).replace('\n', '')

    return [entity]


"""
This function gets a document (a web page) and a relation
 and returns all the entities relevant to this relation
 :parameter doc (html document)
 :parameter relation (string)
 :return entity_lst (list)
"""


def get_rest(doc, relation):
    link_lst = doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'"
                         + relation + "')]//ancestor-or-self::th""/../td//a/@href")
    for i in range(len(link_lst)):
        link_lst[i] = link_lst[i].split('/')[-1]

    text_list = doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'"
                          + relation + "')]//ancestor-or-self::th""/../td//text()[not(ancestor::a)]")

    return link_lst + text_list


# This function returns True if the string s is a foot note
def is_foot_note(s):
    if len(s) == 0:
        return False
    return (s[0] == '[' and s[len(s) - 1] == ']') or '#cite_note' in s


"""
This function gets a string entity that is a possible entity in the ontology,
 and returns True if it contains illegal characters
 :parameter entity (string)
 :return (boolean)
"""


def is_black_listed(entity):
    return '{' in entity or '}' in entity or '\n' in entity \
           or len(entity) == 0 or 'Executive Producer' in entity or is_foot_note(entity) or \
           (len(entity) == 2 and not entity.isalnum())


"""
This function crawls all relevant movies by href and year.
given the url, the function does a DFS traversal on the movie graph.
it traverses each movie, adds all relation too the graph and moves to the next movie.
 :parameter url (string)
 :parameter graph (rdflib.graph.Graph)
"""


def crawler_level1(url, graph):
    r = requests.get(url)
    doc = lxml.html.fromstring(r.content)

    for t in doc.xpath("//table[1]//a[text()>=2010]/parent::td/preceding-sibling::td//a/@href"):
        crawler_level2(t, graph)
        print("finished" + str(t))


"""
  For each move add relations from the infobox to the graph
 :parameter url (string)
 :parameter graph (rdflib.graph.Graph)
"""


def crawler_level2(url, graph):
    r = requests.get(WIKI_PREFIX + url)
    doc = lxml.html.fromstring(r.content)
    movie_name = rdflib.URIRef(f'{EXAMPLE_PREFIX}/{url.replace("/wiki/", "")}')
    # list of all relations in the infobox
    relation_lst = doc.xpath(INFOBOX_VEVENT_PREFIX + "//tr[position()>=3]/th//text()")
    for relation in relation_lst:
        if "'" not in relation and '\n' not in relation and '"' not in relation:
            temp = relation.replace(" ", "_")
            rel = rdflib.URIRef(f'{EXAMPLE_PREFIX}/{temp}')
            # list of all the entities per relation in the infobox
            if relation == 'Release date':
                entity_lst = get_release_date(doc, relation)
            elif relation == 'Running time':
                entity_lst = get_running_time(doc, relation)
            elif relation == 'Based on':
                entity_lst = get_based_on(doc, relation)
            else:
                entity_lst = get_rest(doc, relation)
            for entity in entity_lst:
                temp = entity.strip()
                temp = temp.replace(" ", "_")
                temp = temp.replace('"', "")
                if not is_black_listed(entity):
                    ent = rdflib.URIRef(f'{EXAMPLE_PREFIX}/{temp}')
                    # add to the graph
                    graph.add((movie_name, rel, ent))

    for t in doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'Directed')]/..//a/@href"):
        crawler_level3(t, graph)

    for t in doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'Produced')]/..//a/@href"):
        crawler_level3(t, graph)

    for t in doc.xpath(INFOBOX_VEVENT_PREFIX + "//*[contains(text(),'Starring')]/..//a/@href"):
        crawler_level3(t, graph)


"""
  For each person add relations from the infobox to the graph
 :parameter url (string)
 :parameter graph (rdflib.graph.Graph)
"""


def crawler_level3(url, graph):
    r = requests.get(WIKI_PREFIX + url)
    doc = lxml.html.fromstring(r.content)

    person_name = rdflib.URIRef(f'{EXAMPLE_PREFIX}/{url.replace("/wiki/", "")}')
    # list of all relations in the infobox
    relation_lst = doc.xpath(INFOBOX_BIOGRAPHY_PREFIX + "//tr[position()>=3]/th//text()")
    for relation in relation_lst:
        if "'" not in relation and '\n' not in relation and '"' not in relation:
            temp = relation.replace(" ", "_")
            rel = rdflib.URIRef(f'{EXAMPLE_PREFIX}/{temp}')
            # list of all the entities per relation in the infobox
            if relation == 'Born':
                entity_lst = get_bday(doc, relation)
            elif relation == 'Occupation':
                entity_lst = get_occupation(doc, relation)
            else:
                entity_lst = doc.xpath(INFOBOX_BIOGRAPHY_PREFIX + "//*[contains(text(),'"
                                       + relation + "')]//ancestor-or-self::th""/../td//text()")
            for entity in entity_lst:
                temp = entity.strip()
                temp = temp.replace(" ", "_")
                temp = temp.replace('"', "")
                if not is_black_listed(entity):
                    ent = rdflib.URIRef(f'{EXAMPLE_PREFIX}/{temp}')
                    # add to the graph
                    graph.add((person_name, rel, ent))


"""
  create the ontology by calling crawl_level1() and serializing the graph
"""


def create_ontology():
    graph = rdflib.Graph()
    crawler_level1(URL, graph)
    graph.serialize(ONTOLOGY_NAME, format="nt")


def my_query(entity_name, relation):
    g = rdflib.Graph()
    g.parse(ONTOLOGY_NAME, format="nt")
    query = "SELECT * WHERE {"
    query += "<http://example.org/" + entity_name + "> "
    query += "<http://example.org/" + relation + "> "
    query += "?s }"
    ret = g.query(query)
    return list(ret)


def based_on_query():
    g = rdflib.Graph()
    g.parse(ONTOLOGY_NAME, format="nt")
    query = """SELECT * WHERE { ?s <http://example.org/Based_on> ?x }"""
    ret = g.query(query)
    return list(ret)


def starring_query(entity_name):
    g = rdflib.Graph()
    g.parse(ONTOLOGY_NAME, format="nt")
    query = "SELECT * WHERE {"
    query += "?s "
    query += "<http://example.org/Starring> "
    query += "<http://example.org/" + entity_name + "> }"
    ret = g.query(query)
    return list(ret)


def occupation_query(occupation1, occupation2):
    g = rdflib.Graph()
    g.parse(ONTOLOGY_NAME, format="nt")
    query = "SELECT * WHERE {"
    query += "?s "
    query += "<http://example.org/Occupation> "
    query += "<http://example.org/" + occupation1 + ">. "
    query += "?s "
    query += "<http://example.org/Occupation> "
    query += "<http://example.org/" + occupation2 + ">. }"
    ret = g.query(query)
    return list(ret)


def print_answer(ans_list):
    for i in range(len(ans_list) - 1):
        print(ans_list[i], end=', ')

    print(ans_list[len(ans_list) - 1])


def query_parser(query):
    ans_lst = []
    query = query.replace('?', '')
    token_lst = query.split()
    if token_lst[0] == 'Who':
        movie_name = "_".join(token_lst[2:])
        if token_lst[1] == 'directed':
            relation = "Directed_by"
        elif token_lst[1] == 'produced':
            relation = "Produced_by"
        elif token_lst[1] == 'edited':
            relation = "Edited_by"
        elif token_lst[1] == 'starred':
            relation = "Starring"
            index = token_lst.index("in")
            movie_name = "_".join(token_lst[index + 1:])
        else:
            return
        ans = my_query(movie_name, relation)
        for element in ans:
            ans_lst.append((str(element[0]).split('/')[-1]).replace('_', ' '))

    elif token_lst[0] == 'When':
        entity_name = "_".join(token_lst[2:len(token_lst) - 1])
        if token_lst[len(token_lst) - 1] == 'released':
            relation = "Release_date"
            for ans in my_query(entity_name, relation):
                ans_lst.append((str(ans[0]).split('/')[-1]))
            # relation = "Released"
            # for ans in my_query(entity_name, relation):
            #     ans_lst.append((str(ans[0]).split('/')[-1]))
        elif token_lst[len(token_lst) - 1] == 'born':
            relation = "Born"
            for ans in my_query(entity_name, relation):
                ans_lst.append((str(ans[0]).split('/')[-1]))
        else:
            return
    elif token_lst[0] == 'What':
        index = token_lst.index("of")
        entity_name = "_".join(token_lst[index + 1:])
        if token_lst[3] == 'occupation':
            relation = "Occupation"
            ans = my_query(entity_name, relation)
            for element in ans:
                ans_lst.append((str(element[0]).split('/')[-1]).replace('_', ' '))
        else:
            return
    elif token_lst[0] == 'Did':
        star_index = token_lst.index("star")
        in_index = token_lst.index("in")
        actor = "_".join(token_lst[1:star_index])
        movie = "_".join(token_lst[in_index + 1:])
        actor_lst = my_query(movie, "Starring")
        for element in actor_lst:
            temp = (str(element[0]).split('/')[-1])
            if temp == actor:
                ans_lst = ['Yes']
                return ans_lst
        ans_lst = ['No']
    elif token_lst[0] == 'Is':
        index = token_lst.index("based")
        movie = "_".join(token_lst[1:index])
        book_lst = my_query(movie, "Based_on")
        if len(book_lst) > 0:
            ans_lst = ['Yes']
        else:
            ans_lst = ['No']
    elif token_lst[0] == 'How':
        if token_lst[1] == 'long':
            movie = "_".join(token_lst[3:])
            ans = my_query(movie, "Running_time")
            for element in ans:
                ans_lst.append((str(element[0]).split('/')[-1]).replace('_', ' '))
        elif token_lst[1] == 'many':
            if token_lst[4] == 'based':
                ans_lst = [str(len(based_on_query()))]
            elif token_lst[3] == 'starring':
                won_index = token_lst.index("won")
                entity = "_".join(token_lst[4:won_index])
                movie_lst = starring_query(entity)
                ans_lst = [str(len(movie_lst))]
            else:
                are_index = token_lst.index("are")
                also_index = token_lst.index("also")
                occupation1 = "_".join(token_lst[2:are_index])
                occupation2 = "_".join(token_lst[also_index + 1:])
                ans_lst = [str(len(occupation_query(occupation1, occupation2)))]
    return ans_lst


def test():
    file1 = open('./questions_test.txt', 'r', encoding="utf8")
    Lines = file1.readlines()
    for line in Lines:
        ans_lst = query_parser(str(line))
        if ans_lst is not None and not len(ans_lst) == 0:
            ans_lst.sort()
            print_answer(ans_lst)
        else:
            print()

    file1.close()


# main function to run over NOVA
def main():
    if sys.argv[1] == "create":
        create_ontology()
    else:
        query = ' '.join(sys.argv[1:])
        ans = query_parser(query)
        print_answer(ans)
    return 0


main
