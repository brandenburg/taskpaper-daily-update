# consider i18n

import sys
import codecs
import datetime

# from http://github.com/brandenburg/python-taskpaper
from taskpaper.taskpaper import TaskPaper

import optparse
o = optparse.make_option

DAYS = [
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
    'friday',
    'saturday',
    'sunday'
]

MONTHS = [
    'january',
    'february',
    'march',
    'april',
    'may',
    'june',
    'july',
    'august',
    'september',
    'october',
    'november',
    'december'
]

opts = [
    o('-d', '--day', action='store', dest='day',
      type='choice', choices=DAYS,
      help='pretend today is DAY (default: infer from system date)'),
    o('-s', '--simulate', action='store_true', dest='simulate',
      help="don't write back results to file; dump to stdout instead"),
    o('-r', '--recurring', action='store', dest='recurring',
      help="read recurring tasks from file RECURRING"),
    o('-t', '--tomorrow', action='store_true', dest='tomorrow',
      help="when processing items tagged @monday, @tuesday, etc., tag " +
           "events on the next day with '@tomorrow'"),
    ]

defaults = {
    'day'       : None,
    'simulate'  : False,
    'recurring' : None,
    'tomorrow'  : False,
    }

options = None

def today():
    return DAYS[datetime.date.today().weekday()]

def this_month():
    return MONTHS[datetime.date.today().month - 1]

def merge_recurring(todos, tag):
    if options.recurring:
        for nd in options.recurring[tag]:
            path = nd.path_from_root()
            todos.add_path(path)

def advance_day(todos):
    # convert a given tag to 'today'
    def convert_to(tag, what):
        for nd in todos[tag]:
            nd.drop_tag(tag)
            nd.add_tag(what)

    convert_to_today    = lambda tag: convert_to(tag, 'today')
    convert_to_tomorrow = lambda tag: convert_to(tag, 'tomorrow')

    # everything marked as @tomorrow becomes @today
    convert_to_today('tomorrow')
    # tolerate frequent misspelling
    convert_to_today('tomorow')

    # everything explicitly marked by weekday name becomes @today
    day = today() if options.day is None else options.day
    merge_recurring(todos, day)

    if options.tomorrow:
        # also merge tasks for tomorrow
        day_idx = DAYS.index(day)
        next_day = DAYS[(day_idx + 1) % len(DAYS)]
        merge_recurring(todos, next_day)
        convert_to_tomorrow(next_day)

    convert_to_today(day)

    merge_recurring(todos, 'daily')
    convert_to_today('daily')

    # on certain days also pull in additional items
    # The weekend starts on Saturday.
    if day == 'saturday':
        convert_to_today('weekend')
    # The new (work) week starts on Monday.
    if day == 'monday':
        convert_to_today('nextweek')
        merge_recurring(todos, 'weekly')
        convert_to_today('weekly')

    if datetime.date.today().day == 1 and not options.day:
        merge_recurring(todos, 'monthly')
        merge_recurring(todos, this_month())
        convert_to_today('monthly')
        convert_to_today('nextmonth')
        convert_to_today(this_month())

def drop_done(todos):
    dones = []
    for nd in todos['done']:
        nd.delete()
        dones.append(nd)
    return dones

def drop_should(todos):
    "deferred items: drop @should from @today items to raise awareness"
    for nd in todos['today']:
        nd.drop_tag('should')

def archive_done(todos, archive):
    date  = datetime.date.today()
    today = "%04d-%02d-%02d" % (date.year, date.month, date.day)
    for nd in todos['done']:
        # remove "stale" tags
        for tag in ['today', 'tomorrow', 'weekend', 'nextweek'] + DAYS:
            nd.drop_tag(tag)

        # add to archive
        path = nd.path_from_root()
        new  = archive.add_path(path)

        # check if we added this node before (=> recurrent tasks)
        if u'archived' in new.tags:
            if new.tags[u'archived'] != today:
                # this is a repeated task -> add another 'archived' marker
                new.tags[u'archived'] += ' ' + today
        else:
            new.add_tag(u'archived', today)

        # finally remove the completed node from the todo list
        nd.delete()

def load_file(fname):
    try:
        f = codecs.open(fname, 'r', 'utf8')
        todo = TaskPaper.parse(f)
        f.close()
        return todo
    except IOError as err:
        print "Could not open '%s' (%s)." % (fname, err)
        return None

def write_file(todos, fname):
    try:
        f = codecs.open(fname, 'w', 'utf8')
        f.write(unicode(todos))
        f.close()
        return True
    except IOError as msg:
        print "Could not store '%s' (%s)." % (fname, err)
        return False

def update_file(fname):
    todos = load_file(fname)

    if not todos:
        return None

    archive_fname = fname.replace('.taskpaper', ' Archive.taskpaper')
    archive = load_file(archive_fname)
    if not archive:
        print "Starting new archive: %s" % archive_fname
        archive = TaskPaper()

    drop_should(todos)
    advance_day(todos)
    archive_done(todos, archive)

    if not options.simulate:
        write_file(archive, archive_fname)
        write_file(todos, fname)
    else:
        write_file(archive, '/tmp/todo-archive')
        write_file(todos, '/tmp/todos-dump')
        print unicode(todos)
        print '*' * 80
        print unicode(archive)

def main(args=sys.argv[1:]):
    if options.recurring:
        options.recurring = load_file(options.recurring)
    for fname in args:
        update_file(fname)

if __name__ == '__main__':
    parser = optparse.OptionParser(option_list=opts)
    parser.set_defaults(**defaults)
    (options, files) = parser.parse_args()
    main(files)
