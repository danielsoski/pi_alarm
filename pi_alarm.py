import csv
import os
import signal
import time
import vlc

__all__ = "pi_alarm"
__author__ = "danielsoski"
__version_info__ = (0, 1)
__version__ = "{0}.{1}".format(*__version_info__)

class DanAlarm():
    valid_days = ['next', 'all', 'weekdays', 'weekend']
    valid_am_pm = ['am', 'AM', 'pm', 'PM', '24']
    alarm_name = None
    alarm_time_str = None
    am_pm = None
    alarm_time = None
    alarm_days = None
    alarm_volume = None
    prealarm_profile = None
    alarm_sound_file = None
    audio_player = None
    snooze_enable = False

    def __init__(self):
        pass

    def setup(self, alarm_time, sound_file, alarm_days='all', prealarm_profile=None, snooze_enable=False):
        self.alarm_time = alarm_time
        self.alarm_sound_file = sound_file
        self.audio_player = vlc.MediaPlayer(self.alarm_sound_file)
        self.alarm_days = alarm_days if alarm_days in self.valid_days else None
        if self.alarm_days is None: raise ValueError('Invalid Alarm Days Value. Expecting: ' + ', '.join(self.valid_days))
        self.prealarm_profile = prealarm_profile
        self.snooze_enable = snooze_enable

    def read_config(self, filename=None, alarm_name=None):
        home_dir = os.getenv("HOME") + "/"
        config_dir = "pi_alarm/"
        config_filename = ".config"
        config_loc = home_dir + config_dir + config_filename if filename is None else str(filename)
        if not os.path.exists(config_loc):
            return 1, 'config file does not exist'

        with open(config_loc) as csvfile:
            config_file = csv.DictReader(csvfile, delimiter=',')

            for alarm in config_file:
                if alarm['name'] == alarm_name or alarm_name is None:
                    self.alarm_name = alarm['name']
                    self.alarm_time_str = alarm['alarm_time']
                    self.am_pm = alarm['am_pm'] if alarm['am_pm'] in self.valid_am_pm else None
                    self.alarm_days = alarm['days'] if alarm['days'] in self.valid_days else None
                    self.alarm_time = self.alarm_time_from_str(self.alarm_time_str, self.am_pm, self.alarm_days)
                    self.alarm_volume = alarm['alarm_volume']
                    self.prealarm_profile = alarm['prealarm_profile']
                    self.alarm_sound_file = None
                    self.audio_player = None
                    self.snooze_enable = None

        return 0, ''

    def alarm_time_from_str(self, alarm_time_str, am_pm, days):
        time_now = time.localtime()
        alarm_min = int(alarm_time_str[3:5])
        alarm_hour = int(alarm_time_str[0:2])
        if am_pm == '24':
            alarm_hour = (0 if alarm_hour < 0 else (24 if alarm_hour > 24 else alarm_hour))
        elif am_pm in ['am', 'AM', 'pm', 'PM']:
            alarm_hour = (0 if alarm_hour < 0 else (12 if alarm_hour > 12 else alarm_hour))
            if am_pm == 'pm' or am_pm == 'PM':
                alarm_hour += 12
                if alarm_hour == 24: alarm_hour = 12
            elif am_pm == 'am' or am_pm == 'AM':
                if alarm_hour == 12: alarm_hour = 0
        alarm_time = None
        if days == 'all':
            if alarm_hour > time_now.tm_hour or (alarm_hour == time_now.tm_hour and alarm_min > time_now.tm_min):
                alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour, alarm_min, 0,
                                          time_now.tm_wday, time_now.tm_yday, time_now.tm_isdst))
            else:
                alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour, alarm_min, 0,
                                          time_now.tm_wday, time_now.tm_yday, time_now.tm_isdst)) + 86400
        elif days == 'next':
            alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour, alarm_min, 0,
                                      time_now.tm_wday, time_now.tm_yday, time_now.tm_isdst)) + 86400
        elif days == 'weekdays':
            if time_now.tm_wday < 5:  # is weekday
                if alarm_hour > time_now.tm_hour or (alarm_hour == time_now.tm_hour and alarm_min > time_now.tm_min):
                    alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour,
                                              alarm_min, 0, time_now.tm_wday, time_now.tm_yday, time_now.tm_isdst))
                else:
                    if time_now.tm_wday == 4:  # is friday
                        alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour,
                                                  alarm_min, 0, time_now.tm_wday, time_now.tm_yday,
                                                  time_now.tm_isdst)) + (86400 * 2)
                    else:
                        alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour,
                                                  alarm_min, 0, time_now.tm_wday, time_now.tm_yday,
                                                  time_now.tm_isdst)) + 86400
            else:  # is weekend
                alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour, alarm_min, 0,
                                          time_now.tm_wday, time_now.tm_yday, time_now.tm_isdst)) + (
                                          86400 * (7 - time_now.tm_wday))
        elif days == 'weekend':
            if time_now.tm_wday < 5:  # is weekday
                alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour, alarm_min, 0,
                                          time_now.tm_wday, time_now.tm_yday, time_now.tm_isdst)) + (
                                          86400 * (5 - time_now.tm_wday))
            else:  # is weekend
                if alarm_hour > time_now.tm_hour or (alarm_hour == time_now.tm_hour and alarm_min > time_now.tm_min):
                    alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour,
                                              alarm_min, 0, time_now.tm_wday, time_now.tm_yday,
                                              time_now.tm_isdst)) + 86400
                else:
                    if time_now.tm_wday == 6:  # is sunday
                        alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour,
                                                  alarm_min, 0, time_now.tm_wday, time_now.tm_yday,
                                                  time_now.tm_isdst)) + (86400 * 5)
                    else:
                        alarm_time = time.mktime((time_now.tm_year, time_now.tm_mon, time_now.tm_mday, alarm_hour,
                                                  alarm_min, 0, time_now.tm_wday, time_now.tm_yday,
                                                  time_now.tm_isdst)) + 86400
        return alarm_time

    def time_to_alarm(self):
        return int(self.alarm_time - time.time())

    def time_to_prealarm(self):
        return self.time_to_alarm()  # - self.prealarm_time

    def fire_prealarm(self, signum, frame):
        print('prealarm!')
        if self.time_to_alarm() > 0:
            time.sleep(self.time_to_alarm())
        self.fire_alarm()

    def fire_alarm(self):
        print('alarm!')

    def enter_cmd(self, signum, frame):
        cmd = raw_input('\nEnter CMD: ')
        print('typed: ' + cmd)
        if cmd == 'fire':
            self.fire_alarm()
        signal.pause()

    def start(self):
        signal.signal(signal.SIGALRM, self.fire_prealarm)
        print('setting alarm at ' + self.alarm_time_str + ' in ' + str(self.time_to_prealarm()) + ' sec')
        signal.alarm(self.time_to_prealarm())
        signal.signal(signal.SIGINT, self.enter_cmd)
        signal.pause()

    def test_alarm(self, length=10):
        self.audio_player.play()
        time.sleep(int(length))
        self.audio_player.stop()


def main():
    # argparse
    alarm = DanAlarm()
    alarm.read_config()
    alarm.start()
    # alarm.setup(0, 'beethoven-19-1-bertoglio.mp3')
    # alarm.test_alarm()
    pass

if __name__ == '__main__':
    main()
