# -*- coding: utf-8 -*-
# kate: replace-tabs off; indent-width 4; indent-mode normal
# vim: ts=4:sw=4:noexpandtab

from teer import *
import sys
import math

class MyScheduler(TimerScheduler):
	def __init__(self):
		super(MyScheduler,self).__init__()

sched = MyScheduler()

def main_task():
	def printer(nr):
		counter = 0
		while counter < nr:
			yield TeerPrint(str(counter) + ' (on ' + str(nr) + ')')
			yield WaitDuration(0.5)
			counter += 1
		yield TeerPrint(str(sched.exit_waiting))

	def test_wait_any():
		id1 = yield NewTask(printer(5))
		id2 = yield NewTask(printer(10))
		ret = yield WaitAnyTasks([id1,id2])
		yield KillTasks([id1,id2])
		print ret
	
	def test_wait_all():
		id1 = yield NewTask(printer(5))
		id2 = yield NewTask(printer(10))
		ret = yield WaitAllTasks([id1,id2])
		yield KillTasks([id1,id2])
		print ret
	
	print '\n* Test wait any *\n'
	wait_id = yield NewTask(test_wait_any())
	yield WaitTask(wait_id)
	print '\n * Test wait all *\n'
	wait_id = yield NewTask(test_wait_all())
	yield WaitTask(wait_id)

sched.new(main_task())
print 'Running scheduler'
sched.run()
print 'All tasks are dead, we better leave this place'

