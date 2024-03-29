#!/usr/bin/env python3
# consider i18n

import sys
import codecs
import datetime
import os

# from http://github.com/brandenburg/python-taskpaper
from taskpaper.taskpaper import TaskPaper

DATE_FORMAT = "%d-%m-%Y"
DATE_TAG = "last_updated"

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
    o('-c', '--catch-up', action='store_true',
      help='infer day of last update from archive and run update for all skipped days'),
]

defaults = {
    'day'       : None,
    'simulate'  : False,
    'recurring' : None,
    'tomorrow'  : False,
    'catch_up'  : False,
    'date'      : None,
    }

options = None

ONE_DAY = datetime.timedelta(days=1)

def date():
    return datetime.date.today() if options.date is None else options.date

def infer_date():
    d = datetime.date.today()
    while options.day and DAYS[d.weekday()] != options.day:
        d -= ONE_DAY
    return d

def day_of_week():
    return DAYS[date().weekday()]

def this_month():
    return MONTHS[date().month - 1]

def dates_since(d, until=datetime.date.today()):
    d += ONE_DAY
    while d <= until:
        yield d
        d += ONE_DAY

def merge_recurring(todos, tag):
    if options.recurring:
        for nd in options.recurring[tag]:
            path = nd.path_from_root()
            todos.add_path(path)

def process_countdown(todos, tag):
    for nd in todos[tag]:
        try:
            val = nd.tags[tag]
            if val is None:
                val = 0
            else:
                val = int(val)
            if val > 2:
                nd.tags[tag] = str(val - 1)
            elif val == 2:
                nd.drop_tag(tag)
                nd.add_tag('tomorrow')
            elif val <= 1:
                nd.drop_tag(tag)
                nd.add_tag('today')
        except ValueError:
            pass # silently ignore strings we can't parse

def advance_day(todos):
    # convert a given tag to another given tag (in all nodes)
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
    day = day_of_week()
    merge_recurring(todos, day)

    # process countdowns
    process_countdown(todos, 'indays')
    process_countdown(todos, 'snooze')

    if options.tomorrow:
        # also merge tasks for tomorrow
        day_idx = DAYS.index(day)
        next_day = DAYS[(day_idx + 1) % len(DAYS)]
        merge_recurring(todos, next_day)
        convert_to_tomorrow(next_day)

    merge_recurring(todos, 'daily')
    convert_to_today('daily')

    # on certain days also pull in additional items
    # The weekend starts on Saturday.
    if day == 'saturday':
        convert_to_today('weekend')
    # The new (work) week starts on Monday.
    if day == 'monday':
        for nd in todos['nextweek']:
            arg = nd.tags['nextweek']
            nd.drop_tag('nextweek')
            if arg in DAYS:
                nd.add_tag(arg)
            else:
                nd.add_tag('today')
        merge_recurring(todos, 'weekly')
        convert_to_today('weekly')

    if date().day == 1:
        merge_recurring(todos, 'monthly')
        merge_recurring(todos, this_month())
        convert_to_today('monthly')
        convert_to_today('nextmonth')
        convert_to_today(this_month())

    convert_to_today(day)
    # convert next-week-$DAY tags to just $DAY
    convert_to('n' + day, day)
    convert_to('next' + day, day)


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

def update_date_tag(todos):
    # first, remove any old tags
    for nd in todos[DATE_TAG]:
        nd.drop_tag(DATE_TAG)
    todos[0].add_tag(DATE_TAG, datetime.datetime.now().date().strftime(DATE_FORMAT))

def archive_done(todos, archive):
    today = "%04d-%02d-%02d" % (date().year, date().month, date().day)
    for nd in todos['done']:
        # remove "stale" tags
        for tag in ['today', 'tomorrow', 'weekend', 'nextweek'] + DAYS:
            nd.drop_tag(tag)

        # add to archive
        path = nd.path_from_root()
        new  = archive.add_path(path)

        # check if we added this node before (=> recurrent tasks)
        if 'archived' in new.tags:
            if new.tags['archived'] != today:
                # this is a repeated task -> add another 'archived' marker
                new.tags['archived'] += ' ' + today
        else:
            new.add_tag('archived', today)

        # finally remove the completed node from the todo list
        nd.delete()

def load_file(fname):
    try:
        f = codecs.open(fname, 'r', 'utf8')
        todo = TaskPaper.parse(f)
        f.close()
        return todo
    except IOError as err:
        print("Could not open '%s' (%s)." % (fname, err))
        return None

def last_modification_date(todos, fname):
    try:
        for nd in todos[DATE_TAG]:
            try:
                return datetime.datetime.strptime(nd.tags[DATE_TAG], DATE_FORMAT).date()
            except ValueError:
                continue
        # if that didn't work, try to get the last modification time from the FS
        return datetime.date.fromtimestamp(os.path.getmtime(fname))
    except IOError as err:
        print("Could not get last modification time of '%s' (%s)." % (fname, err))
        return None

def write_file(todos, fname):
    try:
        f = codecs.open(fname, 'w', 'utf8')
        f.write(str(todos))
        f.close()
        return True
    except IOError as msg:
        print("Could not store '%s' (%s)." % (fname, err))
        return False

def update(todos, archive):
    drop_should(todos)
    archive_done(todos, archive)
    advance_day(todos)

def update_file(fname):
    todos = load_file(fname)

    if not todos:
        return None

    archive_fname = fname.replace('.taskpaper', ' Archive.taskpaper')

    archive = load_file(archive_fname)
    if not archive:
        print("Starting new archive: %s" % archive_fname)
        archive = TaskPaper()

    if options.catch_up:
        last_update = last_modification_date(archive, archive_fname)
        if not last_update:
            return None
        for skipped_day in dates_since(last_update):
            # carry out updates that we missed
            options.date = skipped_day
            update(todos, archive)
    else:
        # regular one-shot update
        options.date = infer_date()
        update(todos, archive)

    # date-tag archive for future catchup-mode invocations
    update_date_tag(archive)

    if not options.simulate:
        write_file(archive, archive_fname)
        write_file(todos, fname)
    else:
        write_file(archive, '/tmp/todo-archive')
        write_file(todos, '/tmp/todos-dump')
        print(str(todos))
        print('*' * 80)
        print(str(archive))

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
