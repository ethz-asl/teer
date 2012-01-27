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
			#yield TeerPrint(str(counter))
			yield TeerPrint(str(counter))
			yield WaitDuration(0.5)
			counter += 1
		yield TeerPrint(str(sched.exit_waiting))

	def test_wait_any_all():
		id1 = yield NewTask(printer(5))
		id2 = yield NewTask(printer(10))
		ret = yield WaitAnyTasks([id1,id2])
		print ret
		
	wait_id = yield NewTask(test_wait_any_all())
	yield WaitTask(wait_id)




sched.new(main_task())
sched.run()
print 'Running scheduler'
while sched.taskmap:
	time.sleep(0.3)

print 'All tasks are dead, we better leave this place'

