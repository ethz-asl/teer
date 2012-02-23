# -*- coding: utf-8 -*-
# kate: replace-tabs off; indent-width 4; indent-mode normal
# vim: ts=4:sw=4:noexpandtab

from teer import *
import sys
import math

sched = None

class MyScheduler(TimerScheduler):
	def __init__(self):
		super(MyScheduler,self).__init__()

def main_task():
	def printer(nr):
		counter = 0
		while counter < nr:
			sched.printd(str(counter) + ' (on ' + str(nr) + ')')
			yield WaitDuration(0.5)
			counter += 1
		sched.printd(str(sched.exit_waiting))

	def test_wait_any():
		id1 = sched.new_task(printer(5))
		id2 = sched.new_task(printer(10))
		ret = yield WaitAnyTasks([id1,id2])
		sched.kill_tasks([id1,id2])
		print ret
	
	def test_wait_all():
		id1 = sched.new_task(printer(5))
		id2 = sched.new_task(printer(10))
		ret = yield WaitAllTasks([id1,id2])
		sched.kill_tasks([id1,id2])
		print ret
	
	print '\n* Test wait any *\n'
	wait_id = sched.new_task(test_wait_any())
	yield WaitTask(wait_id)
	print '\n * Test wait all *\n'
	wait_id = sched.new_task(test_wait_all())
	yield WaitTask(wait_id)

sched = MyScheduler()
sched.new_task(main_task())
print 'Running scheduler'
sched.run()
print 'All tasks are dead, we better leave this place'

