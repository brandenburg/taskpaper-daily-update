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

opts = [
    o('-d', '--day', action='store', dest='day',
      type='choice', choices=DAYS,
      help='pretend today is DAY (default: infer from system date)')
    ]

defaults = {
    'day' : None,
    }

options = None

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
    day = today() if options.day is None else options.day
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

def archive_done(todos, archive):
    date  = datetime.date.today()
    today = "%04d-%02d-%02d" % (date.year, date.month, date.day)
    for nd in todos['done']:
        nd.add_tag('archived', today)
        for tag in ['today', 'tomorrow', 'weekend', 'nextweek'] + DAYS:
            nd.drop_tag(tag)
        path = nd.path_from_root()
        archive.add_path(path)
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

    advance_day(todos)
    archive_done(todos, archive)

    write_file(archive, archive_fname)
    write_file(todos, fname)

def main(args=sys.argv[1:]):
    for fname in args:
        update_file(fname)

if __name__ == '__main__':
    parser = optparse.OptionParser(option_list=opts)
    parser.set_defaults(**defaults)
    (options, files) = parser.parse_args()
    main(files)
