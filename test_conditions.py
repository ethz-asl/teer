# -*- coding: utf-8 -*-
# kate: replace-tabs off; indent-width 4; indent-mode normal
# vim: ts=4:sw=4:noexpandtab

from teer import *
import sys
import math

sched = None

class MyScheduler(TimerScheduler):
	chlorophyll_level = ConditionVariable(0.)
	energy_level = ConditionVariable(100)

def chlorophyll_detector():
	yield WaitCondition(lambda: sched.chlorophyll_level > 2)
	print 'We found chlorophyll'
	yield WaitDuration(2)
	print 'Ok, I\'m green enough'

def energy_monitoring():
	yield WaitCondition(lambda: sched.energy_level < 10)
	print 'No more energy, killing all tasks'
	my_tid = sched.get_current_tid()
	sched.kill_all_tasks_except([my_tid])
	print 'Going for lunch'
	yield WaitDuration(1)
	print 'Mission done'
	
def main_task():
	chlorophyll_tid = sched.new_task(chlorophyll_detector())
	energy_tid = sched.new_task(energy_monitoring())
	while True:
		print 'Performing main business'
		yield WaitDuration(1)

sched = MyScheduler()
sched.new_task(main_task())
print 'Running scheduler'
while sched.taskmap:
	# simulate external conditions
	sched.energy_level -= 3
	sched.chlorophyll_level = math.sin(float(sched.energy_level) / 30.) * 4
	# run ready timers
	sched.timer_step()
	# wait
	time.sleep(0.3)
	print 'Ext var: energy_level=' +str(sched.energy_level)+', chlorophyll_level='+str(sched.chlorophyll_level)
print 'All tasks are dead, we better leave this place'

