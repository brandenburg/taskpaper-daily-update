# consider i18n

import sys
import codecs
import datetime

# from http://github.com/brandenburg/python-taskpaper
from taskpaper.taskpaper import TaskPaper

DAYS = [
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday'
]

def today():
    return DAYS[datetime.date.today().weekday()]

def advance_day(todos):
    # convert a given tag to 'today'
    def convert_to_today(tag):
        for nd in todos[tag]:
            nd.drop_tag(tag)
            nd.add_tag('today')

    # everything marked as @tomorrow becomes @today
    convert_to_today('tomorrow')

    # everything explicitly marked by weekday name becomes @today
    day = today()
    convert_to_today(day)

    # on certain days also pull in additional items
    # The weekend starts on Saturday.
    if day == 'saturday':
        convert_to_today('weekend')
    # The new (work) week starts on Monday.
    if day == 'monday':
        convert_to_today('nextweek')

def drop_done(todos):
    dones = []
    for nd in todos['done']:
        nd.delete()
        dones.append(nd)
    return dones

def testfile():
    return codecs.open('test.taskpaper', 'r', 'utf8')

def test():
    td = TaskPaper.parse(testfile())


    it = list(td['today'])[0]
    print it.tags
    it.add_tag('foo')
    print it.tags
    it.drop_tag('done')
    it.drop_tag('foo')
    print it.tags


    for nd in td['today']:
        print nd

    print td[2]

    print 'pre:', len(list(td.select(lambda _: True)))

    for nd in td['today']:
        nd.delete()

    print len(list(td['today'])), len(list(td.select(lambda _:True)))

def update(todos):
    advance_day(todos)
    drop_done(todos)

def test2():
    td = TaskPaper.parse(testfile())
    update(td)
    print unicode(td.format(lambda nd: 'today' in nd.tags))

def main(args=sys.argv[1:]):
    if len(args) == 1:
        f = codecs.open(args[0], 'r', 'utf8')
        todo = TaskPaper.parse(f)
        f.close()

#        for nd in todo.select(lambda nd: nd.is_project()):
#            print nd

        update(todo)

        f = codecs.open(args[0], 'w', 'utf8')
        f.write(unicode(todo))
        f.close()

#        for nd in todo:
#            print unicode(nd)
#        print unicode(todo)



if __name__ == '__main__':
    main()
#    test2()
