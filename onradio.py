import subprocess, os, time, thread, multiprocessing, datetime, sys, urllib, pickle
from xml.dom import minidom

say_c = "espeak \"{0}\""  # "pico2wave -w temp.wav \"{0}\";aplay temp.wav > /dev/null 2>&1"

def sync_():
    print("Fetching Icecast Channel List")
    try:
        data = urllib.urlopen("http://dir.xiph.org/yp.xml").read()
    except:
        print("Sync Error, Try later")
        sys.exit()
    doc = minidom.parseString(data)
    stations = []
    counter = 0
    for post in doc.getElementsByTagName("entry"):
        try:
            stations.append(dict(id=counter,
                                 name=post.getElementsByTagName("server_name")[0].firstChild.data,
                                 ip=post.getElementsByTagName("listen_url")[0].firstChild.data,
                                 genre=post.getElementsByTagName("genre")[0].firstChild.data))
            counter += 1
        except:
            pass
    pickle.dump(stations, open("stations.dat", 'w'))
    print("Done Sync")
    return stations


def StationsHandler():
    try:
        stations = pickle.load(open("stations.dat", "r"))
    except:
        stations = sync_()
    g_ = []
    for i in range(0, len(stations)):
        if not (stations[i]["genre"] in g_):
            g_.append(stations[i]["genre"])
    return stations, g_


class PlayStream():
    def __init__(self, q):
        self.main = None
        while True:
            a = q.get()
            if a == "CROSS" or a == "UCROSS":
                try:
                    if a == "CROSS":
                        self.Fade(True)
                    else:
                        self.Fade(False)
                except:
                    pass
            elif a == "STOP":
                try:
                    self.Fade(True)
                    self.main.kill()
                except:
                    pass
            elif a[0] == "TIMER":
                thread.start_new_thread(self.TimerStart, (float(a[1]),))
            elif a[0] == "SAY":
                thread.start_new_thread(self.say_, (a[1],))
            else:
                try:
                    self.Fade(True)
                    self.main.kill()
                except:
                    pass
                os.system(say_c.format("Now Playing " + a[0][0]))
                self.main = subprocess.Popen(['mplayer', a[0][1]], stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, stdin=subprocess.PIPE)
                thread.start_new_thread(self.mon, ())

    def mon(self):
        before = ""
        while True:
            try:
                line = self.main.stdout.readline()
                if line.startswith('ICY Info:'):
                    a = line.split('=')[1]
                    now = a[0:len(a) - 2]
                    if not (before == now):
                        self.Fade(True)
                        os.system(say_c.format(now))
                        self.Fade(False)
                    before = now
                    time.sleep(2)
            except:
                break

    def Fade(self, fade_):
        try:
            for i in range(0, 31):
                if fade_:
                    self.main.stdin.write('9')
                else:
                    self.main.stdin.write('0')
                time.sleep(0.1)
        except:
            pass

    def TimerStart(self, tm):
        self.say_("Sleep timer set for " + str(tm) + " minutes")
        time.sleep(float(tm) * 60)
        self.Fade(True)
        self.main.kill()

    def say_(self, txt):
        self.Fade(True)
        os.system(say_c.format(txt))
        self.Fade(False)


q_ = multiprocessing.Queue()
a = multiprocessing.Process(target=PlayStream, args=(q_,))
a.start()

print("""
Commands.

stop
time
list genre
list stations
play <station id>
""")
def ask():
    q = raw_input(">")
    try:
        if q.startswith("play"):
            for i in range(0, len(stations)):
                if stations[i]['id'] == int(q.split()[1]):
                    q_.put([[stations[i]['name'], stations[i]['ip']]])
        elif q == "time":
            q_.put(["SAY", "The Time is " + datetime.datetime.now().strftime("%-I %M %p")])
        elif q.startswith("sleep"):
            q_.put(["TIMER", float(q.split()[1])])
        elif q == "stop":
            q_.put("STOP")
        elif q.split()[0] == "list" and q.split()[1] == "genre":
            if len(q.split()) == 3:
                for i in range(0, len(g_)):
                    if (g_[i]).upper().find(' '.join(q.split()[2:len(q.split())])) > -1:
                        print(str(i) + " " + g_[i])
            else:
                for i in range(0, len(g_)):
                    print(str(i) + " " + g_[i])
        elif q.split()[0] == "list" and q.split()[1] == "stations":
            if len(q.split()) == 3:
                for i in range(0, len(stations)):
                    if stations[i]['genre'] == g_[int(q.split()[2])]:
                        print(str(stations[i]['id']).zfill(2) + " " + stations[i]['name'])
            else:
                for i in range(0, len(stations)):
                    print(str(stations[i]['id']).zfill(2) + " " + stations[i]['name'])
        else:
            print("wrong command")
    except:
        pass


stations, g_ = StationsHandler()
ask()

while True:
    ask()
