from hull_scraper import graph_search, get_regent_list, get_unfinished_person
#regent_list = get_regent_list()
count = 0
while count < float('inf'):
    try:
        next_ = get_unfinished_person()
    except StopIteration:
        break
    graph_search(next_['path'], limit=40)
    count += 1
    print "Nr. of restarts: {}".format(count)
