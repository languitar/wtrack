#!/usr/bin/env python2

from __future__ import print_function

import argparse
import errno
import os.path
import urllib2
import sys

import icalendar
import numpy as np
import pandas as pd


CONFIG_FILE = os.path.expanduser('~/.config/wtrack/config.ini')
DATA_DIR = os.path.expanduser('~/.local/share/wtrack')
TIMES_FILE = os.path.join(DATA_DIR, 'times.csv')
TARGETS_FILE = os.path.join(DATA_DIR, 'targets.csv')

_TIMES_COLUMNS = ['start', 'end', 'correction', 'description']
_TARGETS_COLUMNS = ['target', 'description']


def _read_data(filename):
    with open(filename, 'r') as fd:
        return pd.read_csv(fd, index_col=0)


def _read_times(filename):
    try:
        data = _read_data(filename)
        data['start'] = pd.to_datetime(data['start'])
        data['end'] = pd.to_datetime(data['end'])
        data['correction'] = pd.to_timedelta(data['correction'])
        data['description'] = data['description'].fillna('')
        data = data.sort('start')
        return data
    except IOError as error:
        if error.errno == errno.ENOENT:
            # file simply does not exist. We probably start from the beginning
            return pd.DataFrame(
                index=pd.DatetimeIndex([]),
                columns=_TIMES_COLUMNS)
        else:
            raise error


def _read_targets(filename):
    try:
        targets = _read_data(filename)
        targets.index = pd.to_datetime(targets.index)
        targets['target'] = pd.to_timedelta(targets['target'])
        targets = targets.sort_index()
        return targets
    except IOError as error:
        if error.errno == errno.ENOENT:
            # file simply does not exist. We probably start from the beginning
            return pd.DataFrame(
                index=pd.DatetimeIndex([]),
                columns=_TARGETS_COLUMNS)
        else:
            raise error


def _write_data(data, filename, columns):
    try:
        os.makedirs(os.path.dirname(filename))
    except OSError as error:
        if not (error.errno == errno.EEXIST and
                os.path.isdir(os.path.dirname(filename))):
            raise error
    with open(filename, 'w') as fd:
        data.to_csv(fd, columns=columns)


def _read_public_holidays(url):
    response = urllib2.urlopen(url)
    calendar = icalendar.Calendar.from_ical(response.read())
    dates = []
    descriptions = []
    for component in calendar.walk():
        if component.name == "VEVENT":
            dates.append(component.get('dtstart').dt)
            descriptions.append(component.get('summary'))
    return pd.Series(descriptions, index=pd.to_datetime(dates))


_holidays = {}


def _get_holidays(year):
    # TODO url, threading
    global _holidays
    if int(year) not in _holidays:
        _holidays[int(year)] = _read_public_holidays(
            'http://www.schulferien.org/iCal/Feiertage/icals/'
            'Feiertage_Nordrhein_Westfalen_{}.ics'.format(year))
    return _holidays[int(year)]


def _get_default_target(date):
    if date.dayofweek >= 5:
        # weekend
        return pd.Timedelta(0), 'weekend'
    elif pd.datetools.normalize_date(date) in _get_holidays(date.year):
        return pd.Timedelta(0), _get_holidays(date.year)[pd.datetools.normalize_date(date)]
    else:
        # TODO from config
        return pd.Timedelta('8h'), ''


def _interpolate_targets(targets, start, end):
    new_index = pd.Series(np.concatenate([
        pd.date_range(
            pd.datetools.normalize_date(start),
            pd.datetools.normalize_date(end)),
        targets.index]))
    new_index.sort()
    new_index = new_index.drop_duplicates()
    targets = targets.reindex(new_index)

    def fill_missing_target(row):
        if not row['target'] is pd.NaT:
            return row
        else:
            date = pd.datetools.normalize_date(row['index'])
            target, description = _get_default_target(date)
            print(
                'Assuming target work time for {}: {} '
                '(description: {})'.format(date, target, description))
            return pd.Series({'index': row['index'],
                              'target': target,
                              'description': description})

    return targets.reset_index().apply(
        fill_missing_target, axis=1).set_index('index')


def main_track(args):
    times = _read_times(TIMES_FILE)
    targets = _read_targets(TARGETS_FILE)

    start = pd.to_datetime(args.start)
    end = pd.to_datetime(args.end)
    correction = pd.to_datetime(args.correction)
    description = args.description

    # --- validity checks
    # start before end, same timestamp is allowed to simply input corrections
    if end < start:
        print(
            'ERROR: End time before start time '
            '(start: {}, end: {})'.format(start, end),
            file=sys.stderr)
        sys.exit(1)
    # overlaps
    overlaps = pd.concat([
        times[(times['end'] > start) & (times['end'] < end)],
        times[(times['start'] > start) & (times['start'] < end)],
        times[(times['start'] <= start) & (times['end'] >= end)]
    ])
    if not overlaps.empty:
        print(
            'ERROR: New entry overlaps with existing ones'
            '(start: {}, end: {}):\n{}'.format(start, end, overlaps),
            file=sys.stderr)
        sys.exit(1)
    # work past midnight
    if pd.datetools.normalize_date(end) > pd.datetools.normalize_date(start):
        print(
            'ERROR: Work across day boundary not supported '
            '(start: {}, end: {})'.format(start, end),
            file=sys.stderr)
        sys.exit(1)

    print('''Adding entry:
  Start: {start}
  End: {end}
  Correction: {correction}
  Description: {description}'''.format(
        start=start, end=end, correction=correction, description=description))

    times.loc[len(times)] = [start, end, correction, description]
    times = times.sort('start')

    # add missing targets
    targets = _interpolate_targets(targets,
                                   times['start'].min(),
                                   times['end'].max())

    # if everything succeeded, write data
    _write_data(times, TIMES_FILE, _TIMES_COLUMNS)
    _write_data(targets, TARGETS_FILE, _TARGETS_COLUMNS)


def main_target(args):
    targets = _read_targets(TARGETS_FILE)

    date = pd.datetools.normalize_date(pd.to_datetime(args.date))

    if args.target is None:
        # just show the report

        if date not in targets.index:
            # not in database so far
            target, description = _get_default_target(date)
            print('Predicted target work time for {}: '
                  '{} (description: {})'.format(date, target, description))
        else:
            row = targets.loc[date]
            print('Target work time for {}: {} (description: {})'.format(
                date, row['target'], row['description']))

    else:
        # insert a new target

        target = pd.to_timedelta(args.target)
        print('Setting new target for {}: {} (description: )'.format(
            date, target, args.description))
        targets.loc[date] = [target, args.description]
        _write_data(targets, TARGETS_FILE, _TARGETS_COLUMNS)


def main_report(args):
    times = _read_times(TIMES_FILE)
    targets = _read_targets(TARGETS_FILE)

    # ensure that we have targets for all data we know
    targets = _interpolate_targets(targets,
                                   times['start'].min(),
                                   times['end'].max())

    raw_hours = times['end'] - times['start']
    raw_hours.replace(pd.NaT, pd.Timedelta(0))
    times['worktime'] = raw_hours + times['correction'].fillna(0)
    times.index = times['start'].apply(pd.datetools.normalize_date)

    deltas = times[['worktime']]
    deltas = deltas.resample('1d', how='sum')
    deltas['target'] = targets['target'].reindex(deltas.index)
    deltas['diff'] = deltas['target'] - deltas['worktime']

    # limit everything to this year
    deltas = deltas[deltas.index >= pd.to_datetime(pd.to_datetime('now').year)]

    # weekly work time
    weekly_worktime = times['worktime'].resample('w', how='sum')
    print(weekly_worktime)
    weekly_worktime.index = weekly_worktime.index.to_series().apply(
        lambda x: x.weekofyear)
    weekly_worktime = weekly_worktime.apply(lambda x: x.astype(float) /
                                            1000000000 / 60 / 60)
    print(weekly_worktime)

    # weekly differences
    print(deltas['diff'].resample('w', how='sum').apply(
        lambda x: x.astype(float) / 1000000000 / 60 / 60))


def main():

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='subcommands')

    track = subparsers.add_parser('track',
                                  description='Add a bunch of work')
    track.set_defaults(func=main_track)
    track.add_argument(
        '-c', '--correction',
        metavar='TIMEDELTA',
        default='-0.5h',
        help='correction factor as pandas-parseable timedelta')
    track.add_argument(
        'start',
        help='start time of work, pandas-parseable format')
    track.add_argument(
        'end',
        help='end time of work, pandas-parseable format')
    track.add_argument(
        'description',
        default='',
        nargs='?',
        help='description of activity')

    target = subparsers.add_parser(
        'target',
        description='Get or set the target work time for a day')
    target.set_defaults(func=main_target)
    target.add_argument(
        'date',
        help='date for which to set the target work time, pandas-parseable')
    target.add_argument(
        'target',
        metavar='TIMEDELTA',
        nargs='?',
        help='time to work at this day')
    target.add_argument(
        'description',
        default='',
        nargs='?',
        help='description of activity')

    report = subparsers.add_parser(
        'report',
        description='Reports on the work time')
    report.set_defaults(func=main_report)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

