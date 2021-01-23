#!/usr/bin/python

import os
import sys
import traceback
import time
import json
import threading
import sqlite3
import datetime
import pytz
import wsservice

DEFAULT_LOG_PERIOD = datetime.timedelta(hours=1)

def datetime_converter(val):
    datepart, timepart = val.split(" ")
    year, month, day = map(int, datepart.split("-"))
    timepart_full = timepart.split("+")
    hours, minutes, seconds = map(int, timepart_full[0].split(":"))
    val = datetime.datetime(
        year, month, day, hours, minutes, seconds,
        tzinfo=pytz.utc)
    return val

class Room:
    def __init__(self, conf):
        self.name = conf['name']
        self.key = conf['key']
        self.conf = conf
        self.representative = False
        self.temperature = None
        self.humidity = None
        self.pressure = None
        self.date = None
        self.value_file_temperature = None
        self.value_file_humidity = None
        self.value_file_pressure = None

        if 'representative' in conf and conf['representative']:
            self.representative = True
        
        if 'value-files' in conf:
            vf = conf['value-files']
            if 'temperature' in vf:
                self.value_file_temperature = vf['temperature']
            if 'humidity' in vf:
                self.value_file_humidity = vf['humidity']
            if 'pressure' in vf:
                self.value_file_pressure = vf['pressure']

    def update(self, date, temperature, humidity, pressure):
        self.date = date.astimezone(pytz.utc) if date else None
        self.temperature = temperature
        self.humidity = humidity
        self.pressure = pressure
        if self.value_file_temperature:
            self.temperature = self._value_in_file(self.value_file_temperature)
        if self.value_file_humidity:
            self.humidity = self._value_in_file(self.value_file_humidity)
        if self.value_file_pressure:
            self.pressure = self._value_in_file(self.value_file_pressure)

    def _value_in_file(self, path):
        try:
            with open(path, 'r') as f:
                return float(f.readline().split()[0])
        except:
            print(traceback.format_exc())
            print('roomenv: path: {0}'.format(path))
            return None

class Rooms:
    def __init__(self, conf):
        self.conf = conf
        self.logging_conf = {}
        self.rooms_conf = []
        self.dbpath = None
        self.rooms = {}
        self.representative = None

        if 'room-environment-logging' in conf.main:
            self.logging_conf = conf.main['room-environment-logging']
            if 'dbdir' in self.logging_conf:
                self.dbpath = self.logging_conf['dbdir']+'/wserver_room_env.db'
                con = sqlite3.connect(
                    self.dbpath,
                    detect_types=sqlite3.PARSE_DECLTYPES | \
                                 sqlite3.PARSE_COLNAMES)
                sqlite3.dbapi2.converters['DATETIME'] = datetime_converter
                cur = con.cursor()
                cur.execute(
                    'CREATE TABLE IF NOT EXISTS envlog '
                    '(key TEXT, date DATETIME, '
                    'temperature REAL, humidity REAL, pressure REAL)')
                cur.execute(
                    'CREATE INDEX IF NOT EXISTS envlogix '
                    'ON envlog (key, date)')
                con.close()

        if 'rooms' in conf.main:
            self.rooms_conf = conf.main['rooms']

        for rconf in self.rooms_conf:
            if 'name' in rconf and 'key' in rconf:
                room = Room(rconf)
                self.rooms[room.key] = room
                if room.representative:
                    self.representative = room
        if self.representative is None and self.rooms:
            room = self.rooms[self.rooms_conf[0]['key']]
            room.representative = True
            self.representative = room

    def currentData(self, key):
        return self.rooms[key]
                
    def update(self, key, date,
               temperature=None, humidity=None, pressure=None):
        if key in self.rooms:
            room = self.rooms[key]
            room.update(date, temperature, humidity, pressure)
            if self.dbpath:
                con = sqlite3.connect(
                    self.dbpath,
                    detect_types=sqlite3.PARSE_DECLTYPES | \
                                 sqlite3.PARSE_COLNAMES)
                sqlite3.dbapi2.converters['DATETIME'] = datetime_converter
                cur = con.cursor()
                cur.execute(
                    'INSERT INTO '
                    'envlog (key, date, temperature, humidity, pressure) '
                    'VALUES(?, ?, ?, ?, ?)',
                    [room.key, room.date, room.temperature,
                     room.humidity, room.pressure])
                con.commit()
                con.close()

    def getRooms(self):
        return map(lambda conf: self.rooms[conf['key']], self.rooms_conf)

    def getRoom(self, key):
        if key in self.rooms:
            return self.rooms[key]
        else:
            return None

    def getLog(self, key, date_from=None, date_to=None):
        if key in self.rooms and self.dbpath:
            if date_from is None:
                if date_to is None:
                    date_to = datetime.datetime.now(pytz.utc)
                date_from = date_to - DEFAULT_LOG_PERIOD
            elif date_to is None:
                date_to = date_from + DEFAULT_LOG_PERIOD
            date_from = date_from.astimezone(pytz.utc)
            date_to = date_to.astimezone(pytz.utc)
            def factory(cur, row):
                return {
                    'date': str(row[0]),
                    'timestamp': int(row[0].strftime('%s')),
                    'temperature': row[1],
                    'humidity': row[2],
                    'pressure': row[3]
                }
            con = sqlite3.connect(
                self.dbpath,
                detect_types=sqlite3.PARSE_DECLTYPES | \
                             sqlite3.PARSE_COLNAMES)
            sqlite3.dbapi2.converters['DATETIME'] = datetime_converter
            con.row_factory = factory
            cur = con.cursor()
            for i in range(5):
                try:
                    cur.execute(
                        'SELECT date, temperature, humidity, pressure '
                        'FROM envlog '
                        'WHERE key = ? AND date >= ? AND date <= ?',
                        [key, date_from, date_to])
                    result = cur.fetchall()
                except sqlite3.OperationalError:
                    print('-------------------------------------------------')
                    print(traceback.format_exc())
                    print('-------------------------------------------------')
                    time.sleep(0.5)
            cur.close()
            con.close()
            return result
            
        else:
            return []
