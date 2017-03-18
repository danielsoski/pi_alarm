import csv
import os
import signal
import time
import subprocess
import argparse

__all__ = "pi_alarm"
__author__ = "danielsoski"
__version_info__ = (0, 1)
__version__ = "{0}.{1}".format(*__version_info__)

class PiAlarm():
    config_titles = ['name','alarm_time','am_pm','days','alarm_volume','alarm_sound_file','prealarm_profile','snooze_enable']
    valid_days = ['next', 'all', 'weekdays', 'weekend']
    valid_am_pm = ['am', 'AM', 'pm', 'PM', '24']
    alarm_name = None
    alarm_time_str = None
    am_pm = None
    alarm_time = None
    alarm_days = None
    alarm_volume = None
    alarm_sound_file = None
    prealarm_profile_str = None
    prealarm_enable = False
    prealarm_profile = None
    prealarm_time = None
    snooze_enable = False
    prealarm_audio = None
    alarm_audio = None

    def __init__(self):
        pass

    def setup(self, alarm_time_str, am_pm, sound_file, alarm_volume, alarm_days='all', prealarm_profile_str='0', snooze_enable=False):
        self.alarm_time_str = alarm_time_str
        self.am_pm = am_pm
        self.alarm_days = alarm_days if alarm_days in self.valid_days else None
        if self.alarm_days is None: raise ValueError('Invalid Alarm Days Value. Expecting: ' + ', '.join(self.valid_days))
        self.alarm_time = self.alarm_time_from_str(self.alarm_time_str, self.am_pm, self.alarm_days)
        self.alarm_volume = int(alarm_volume)
        self.alarm_sound_file = sound_file
        if not os.path.isfile(self.alarm_sound_file):
            print('ERR: Alarm sound file does not exist')
            sys.exit()
        self.prealarm_profile_str = prealarm_profile_str
        self.parse_prealarm_profile_str()
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
                    self.parse_config_dict(alarm)

        return 0, ''

    def parse_config_dict(self, config_dict):
        alarm = config_dict
        self.alarm_name = alarm['name']
        self.alarm_time_str = alarm['alarm_time']
        self.am_pm = alarm['am_pm'] if alarm['am_pm'] in self.valid_am_pm else None
        self.alarm_days = alarm['days'] if alarm['days'] in self.valid_days else None
        self.alarm_time = self.alarm_time_from_str(self.alarm_time_str, self.am_pm, self.alarm_days)
        self.alarm_volume = int(alarm['alarm_volume'])
        self.alarm_sound_file = alarm['alarm_sound_file']
        if not os.path.isfile(self.alarm_sound_file):
            print('ERR: Alarm sound file does not exist')
            sys.exit()
        self.prealarm_profile_str = alarm['prealarm_profile']
        self.parse_prealarm_profile_str()
        self.snooze_enable = None

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

    def parse_prealarm_profile_str(self):
        profile = self.prealarm_profile_str.split('-')
        # Profile 0 - Constant Volume: Argument 1 is the volume of the prealarm. Argument 2 is the length in minutes.
        # Example: 0-10-15 (volume 10% for 15 minutes) or 0-0-# (no prealarm)
        if profile[0] == '0':
            if len(profile) == 3 and profile[1].isdigit() and profile[2].isdigit():
                vol = int(profile[1])
                dur = int(profile[2])
                if vol == 0:
                    self.prealarm_enable = False
                    return
                elif vol > 0 and dur > 0:
                    self.prealarm_time = dur * 60
                    self.prealarm_profile = profile
                    self.prealarm_enable = True
                else:
                    print('ERR: Incorrect prealarm profile syntax')
                    sys.exit()
            else:
                print('ERR: Incorrect prealarm profile syntax')
                sys.exit()
        
        # Profile 1 - Linear Volume Ramp: Argument 1 is the time in minutes of the ramp.
        # Volume ramps from 0% to alarm volume
        # Example: 1-10
        if profile[0] == '1':
            if (len(profile) != 2) or (not profile[1].isdigit()):
                print('ERR: Incorrect prealarm profile syntax')
                sys.exit()
            elif int(profile[1]) == 0:
                print('ERR: Cannot have prealarm of length 0 min')
                sys.exit()
            self.prealarm_time = int(profile[1]) * 60
        
        self.prealarm_enable = True
        self.prealarm_profile = profile

    def set_pi_volume(self, volume):
        return subprocess.call(['amixer','set','PCM','--',str(volume)+'%'], stdout = subprocess.PIPE)

    def time_to_alarm(self):
        return int(self.alarm_time - time.time())

    def time_to_prealarm(self):
        return self.time_to_alarm() - self.prealarm_time

    def fire_prealarm(self, signum, frame):
        print('prealarm!')
        if self.prealarm_profile[0] == '1':
            self.set_pi_volume(0)
            self.prealarm_audio = subprocess.Popen(['mpg123','--loop', '-1',self.alarm_sound_file], stdout = subprocess.PIPE, stderr = subprocess.PIPE)
            while self.time_to_alarm() > 0:
                target_vol = int(float(self.prealarm_time - self.time_to_alarm()) / self.prealarm_time * self.alarm_volume)
                print('Setting volume to '+str(target_vol))
                self.set_pi_volume(target_vol)
                time.sleep(1)
        self.fire_alarm()

    def fire_alarm(self, signum=None, frame=None):
        print('alarm!')
        print('Setting volume to '+str(self.alarm_volume))
        self.set_pi_volume(self.alarm_volume)
        signal.pause()
        self.prealarm_audio.terminate()
        self.set_pi_volume(0)

    def enter_cmd(self, signum, frame):
        cmd = raw_input('\nEnter CMD: ')
        print('typed: ' + cmd)
        if cmd == 'fire':
            self.fire_alarm()
        if cmd == 'kill':
            self.prealarm_audio.terminate()
            self.set_pi_volume(0)
            sys.exit()
        signal.pause()

    def start(self):
        print('setting alarm at ' + self.alarm_time_str + ' in ' + str(self.time_to_alarm()) + ' sec')
        if self.prealarm_enable == True and self.time_to_prealarm() > 0:
            signal.signal(signal.SIGALRM, self.fire_prealarm)
            signal.alarm(self.time_to_prealarm())
            print('prealarm starts '+str(self.prealarm_time/60)+' min before')
        else:
            signal.signal(signal.SIGALRM, self.fire_alarm)
            signal.alarm(self.time_to_alarm())
        signal.signal(signal.SIGINT, self.enter_cmd)
        signal.pause()

def time_str_offset(minutes):
    alarm_hour = int(time.strftime('%H'))
    alarm_min = int(time.strftime('%M')) + minutes
    if alarm_min > 59:
        alarm_min -= 60
        alarm_hour += 1
        if alarm_hour == 24: alarm_hour = 0
    alarm_time = '{:02d}:{:02d}'.format(alarm_hour, alarm_min) 
    return alarm_time

def main():
    parser = argparse.ArgumentParser(description='pi_alarm.py') 
    parser.add_argument('-test_alarm', metavar='<sound_file>', type=str,
                    help='Test the alarm with designated sound file.')
    parser.add_argument('-config', metavar='<config_file>', type=str,
                    help='Set alarm using specified config file location.')
    parser.add_argument('-config_str', metavar='<config_str>', type=str,
                    help='Set alarm using specified config string.')
    parser.add_argument('-name', metavar='<alarm_name>', type=str,
                    help='Name of alarm to use from config file.')
    args = parser.parse_args()

    alarm = PiAlarm()

    if args.test_alarm is not  None:
        alarm.setup(time_str_offset(2), '24', args.test_alarm, 96, prealarm_profile_str='1-1')
    elif args.config_str is not None:
        config_list = args.config_str.split(',')
        config_dict = {}
        for i in range(len(config_list)):
            config_dict[alarm.config_titles[i]] = config_list[i]
        alarm.parse_config_dict(config_dict)
    elif args.config is not None:
        alarm.read_config(filename = args.config, alarm_name = args.name)
    else:
        alarm.read_config()
    
    alarm.start()

if __name__ == '__main__':
    main()
